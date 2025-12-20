"""
Main name extraction processor.

Orchestrates the complete name extraction workflow:
1. Load and merge data
2. Identify reseller types
3. Route to appropriate extractors
4. Extract names and DOBs
5. Validate extracted data
6. Assign unit types based on ages
7. Aggregate errors
8. Return processed DataFrame
"""

import pandas as pd
import logging
from datetime import datetime
from collections import Counter

from config import GYG_MDA_PLATFORM, GYG_STANDARD_PLATFORMS, ALL_GYG_PLATFORMS
from utils.normalization import (
    normalize_ref, normalize_time, normalize_travel_date,
    extract_language_from_product_code,
    extract_tour_type_from_product_code,
    standardize_column_names,
    get_column_value
)
from utils.age_calculator import categorize_age, convert_infant_to_child_for_colosseum
from utils.tix_nom_generator import generate_tix_nom
from utils.scenario_handler import determine_scenario, should_include_monday_columns, ProcessingScenario
from utils.private_notes_parser import parse_private_notes_template
from extractors import GYGStandardExtractor, GYGMDAExtractor, NonGYGExtractor
from utils.private_notes_parser import build_travelers_from_private_notes, supplement_travelers_with_private_notes
from utils.tag_definitions import get_tag_options
from validators import (
    name_has_forbidden_issue,
    check_duplicates_in_booking,
    validate_youth_booking,
    is_eu_country,
    check_unit_traveler_mismatch,
    check_missing_dobs,
    check_all_under_18,
    check_only_child_infant,
    get_unit_counts
)

logger = logging.getLogger(__name__)


class NameExtractionProcessor:
    """
    Main processor for name extraction from Ventrata/Monday data.
    """
    
    def __init__(self, ventrata_df, monday_df=None, update_df=None):
        """
        Initialize processor with data.
        
        Args:
            ventrata_df: Ventrata DataFrame (required)
            monday_df: Monday DataFrame (optional)
            update_df: Update file DataFrame (optional) - previously extracted data
        """
        self.ventrata_df = ventrata_df
        self.monday_df = monday_df
        self.update_df = update_df
        
        # Initialize extractors
        self.extractors = {
            'gyg_standard': GYGStandardExtractor(),
            'gyg_mda': GYGMDAExtractor(),
            'non_gyg': NonGYGExtractor()
        }
        
        # Create column mappings
        self.ventrata_col_map = standardize_column_names(ventrata_df)
        if monday_df is not None:
            self.monday_col_map = standardize_column_names(monday_df)
        else:
            self.monday_col_map = {}
        
        if update_df is not None:
            self.update_col_map = standardize_column_names(update_df)
            # Create ID-to-row mapping for quick lookup
            self._build_update_id_mapping()
            # Validate travel dates match between Ventrata and Update file
            self._validate_travel_dates()
        else:
            self.update_col_map = {}
            self.update_id_map = {}
        
        # Pre-computed error caches
        self.booking_errors_cache = {}
        self.bookings_require_unit_check = set()
        
        # Determine processing scenario
        self.scenario = determine_scenario(ventrata_df, monday_df)
        logger.info(f"Processing scenario: {self.scenario.value}")
        
        if update_df is not None:
            logger.info(f"Update file provided with {len(update_df)} rows and {len(self.update_id_map)} unique IDs")
    
    def process(self):
        """
        Execute the complete name extraction process.
        
        Returns:
            pd.DataFrame: Processed data with columns:
                - Full Name
                - Order Reference
                - Travel Date
                - Unit Type
                - Total Units
                - Tour Time
                - Language
                - Tour Type
                - Private Notes
                - Reseller
                - Error
                
                Plus Monday-specific columns (only if Monday file provided):
                - PNR
                - Ticket Group
                - TIX NOM
        """
        logger.info("Starting name extraction process...")
        
        # Step 1: Pre-process booking-level errors
        logger.info("Pre-processing booking-level errors...")
        self._preprocess_booking_errors()
        
        # Step 2: Determine processing order
        if self.monday_df is not None:
            logger.info(f"Processing in Monday order ({len(self.monday_df)} entries)")
            data_to_process = self._get_monday_ordered_data()
        else:
            logger.info(f"Processing in Ventrata order ({len(self.ventrata_df)} unique bookings)")
            data_to_process = self._get_ventrata_ordered_data()
        
        # Step 3: Process each booking
        results = []
        processed_bookings = set()
        
        for order_ref, booking_data in data_to_process:
            norm_ref = normalize_ref(order_ref)
            
            # Skip if already processed (avoid duplicates)
            if norm_ref in processed_bookings:
                continue
            processed_bookings.add(norm_ref)
            
            # Process this booking
            booking_results = self._process_booking(order_ref, norm_ref, booking_data)
            results.extend(booking_results)
        
        # Step 4: Create results DataFrame
        logger.info(f"Creating results DataFrame with {len(results)} entries")
        results_df = pd.DataFrame(results)
        
        if results_df.empty:
            logger.warning("No data extracted - returning empty DataFrame")
            return pd.DataFrame()
        
        # Step 5: Apply post-processing validations
        results_df = self._apply_post_processing(results_df)
        
        logger.info(f"Name extraction complete: {len(results_df)} entries processed")
        
        return results_df
    
    def _preprocess_booking_errors(self):
        """
        Pre-compute booking-level errors for all GYG bookings.
        
        This optimization calculates errors once per booking instead of
        once per traveler row.
        """
        # Get GYG bookings
        reseller_col = self.ventrata_col_map.get('reseller')
        if not reseller_col:
            logger.warning("No reseller column found - skipping error pre-processing")
            return
        
        # Process ALL GYG bookings (Standard + MDA) together
        # We'll try GYG Standard first in the extraction phase, so pre-compute errors uniformly
        gyg_bookings = self.ventrata_df[
            self.ventrata_df[reseller_col].apply(
                lambda x: any(gyg in str(x) for gyg in ['GetYourGuide', 'Get your Guide'])
            )
        ]
        
        for order_ref in gyg_bookings['_normalized_order_ref'].unique():
            booking_rows = self.ventrata_df[
                self.ventrata_df['_normalized_order_ref'] == order_ref
            ]
            # Determine platform name for error messages
            first_reseller = str(booking_rows.iloc[0][reseller_col])
            platform_name = 'GYG MDA' if 'MDA' in first_reseller else 'GYG Standard'
            
            errors = self._calculate_gyg_booking_errors(booking_rows, platform_name)
            self.booking_errors_cache[order_ref] = errors
        
        logger.info(f"Pre-computed errors for {len(self.booking_errors_cache)} bookings")
    
    def _calculate_gyg_booking_errors(self, booking_rows, platform):
        """Calculate all errors for a GYG booking."""
        errors = []
        
        if booking_rows.empty:
            return errors
        
        # Get booking info
        first_row = booking_rows.iloc[0]
        public_notes_col = self.ventrata_col_map.get('public notes')
        unit_col = self.ventrata_col_map.get('unit')
        
        if not public_notes_col or not unit_col:
            return errors
        
        public_notes = str(first_row[public_notes_col]) if public_notes_col in first_row else ''
        
        # Get unit counts
        unit_counts = get_unit_counts(booking_rows, unit_col)
        child_unit_count = sum(unit_counts.get(unit, 0) for unit in ['Child', 'Infant'])
        adult_unit_count = sum(unit_counts.get(unit, 0) for unit in ['Adult', 'Youth'])
        total_units = child_unit_count + adult_unit_count
        
        has_mixed_units = child_unit_count > 0 and adult_unit_count > 0
        only_child_infant = child_unit_count > 0 and adult_unit_count == 0
        
        # Extract names using fallback pattern: try GYG Standard first, then GYG MDA
        order_ref_for_log = str(first_row.get('Order Reference', 'Unknown'))
        
        # Build booking data dict to pass travel_date for age calculation
        # Note: In error pre-processing, we don't have monday_row, so just use Ventrata
        travel_date = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref_for_log)
        booking_data = {'travel_date': travel_date}
        
        # Try GYG Standard first
        travelers = self.extractors['gyg_standard'].extract_travelers(public_notes, order_ref_for_log, booking_data)
        
        # Fall back to GYG MDA if Standard fails
        if not travelers:
            logger.debug(f"GYG Standard failed for {order_ref_for_log}, trying GYG MDA patterns")
            travelers = self.extractors['gyg_mda'].extract_travelers(public_notes, order_ref_for_log, booking_data)
        total_names = len(travelers)
        
        # Extract DOBs
        dobs = [t.get('dob') for t in travelers if t.get('dob')]
        
        # Validation checks
        unit_error = check_unit_traveler_mismatch(total_units, total_names, platform)
        if unit_error:
            errors.append(unit_error)
        
        dob_error = check_missing_dobs(has_mixed_units, dobs, [t['name'] for t in travelers], platform)
        if dob_error:
            errors.append(dob_error)
        
        # Check for duplicate names
        has_dupes, _ = check_duplicates_in_booking(travelers)
        if has_dupes:
            errors.append(f"Duplicated names in the {platform} booking")
        
        # Check for no names
        if not travelers:
            errors.append(f"No names could be extracted from {platform} booking")
        
        # Check for all under 18
        under_18_error = check_all_under_18(dobs, travel_date, has_mixed_units)
        if under_18_error:
            errors.append(under_18_error)
        
        # Check for only child/infant
        only_child_error = check_only_child_infant(unit_counts)
        if only_child_error:
            errors.append(only_child_error)
        
        return errors
    
    def _get_monday_ordered_data(self):
        """Get bookings in Monday file order."""
        order_ref_col = self.monday_col_map.get('order reference')
        if not order_ref_col:
            logger.error("No order reference column in Monday data")
            return []
        
        data = []
        seen_refs = set()
        for _, row in self.monday_df.iterrows():
            order_ref = row[order_ref_col]
            if pd.isna(order_ref):
                continue
            
            # Normalize order reference to avoid duplicates
            norm_ref = normalize_ref(order_ref)
            if norm_ref in seen_refs:
                continue
            seen_refs.add(norm_ref)
            
            data.append((order_ref, {'monday_row': row}))
            logger.debug(f"Added Monday row for order {order_ref}")
        
        logger.info(f"Prepared {len(data)} bookings from Monday file")
        return data
    
    def _get_ventrata_ordered_data(self):
        """Get unique bookings in Ventrata file order."""
        order_ref_col = self.ventrata_col_map.get('order reference')
        if not order_ref_col:
            logger.error("No order reference column in Ventrata data")
            return []
        
        seen_refs = set()
        ordered_refs = []
        
        for _, row in self.ventrata_df.iterrows():
            ref = row[order_ref_col]
            if pd.isna(ref) or ref in seen_refs:
                continue
            seen_refs.add(ref)
            ordered_refs.append(ref)
        
        return [(ref, {}) for ref in ordered_refs]
    
    def _process_booking(self, order_ref, norm_ref, booking_data):
        """
        Process a single booking and return results for all travelers.
        
        With update file: Check if IDs exist in update file and reuse data,
        only extract names for new IDs.
        
        Args:
            order_ref: Original order reference
            norm_ref: Normalized order reference
            booking_data: Dict with booking info
            
        Returns:
            list: List of result dicts (one per traveler)
        """
        # Get all Ventrata rows for this booking
        ventrata_rows = self.ventrata_df[
            self.ventrata_df['_normalized_order_ref'] == norm_ref
        ]
        
        if ventrata_rows.empty:
            logger.warning(f"No Ventrata data found for order {order_ref}")
            return [{
                'Full Name': '',
                'ID': '',
                'Order Reference': order_ref,
                'Unit Type': '',
                'Total Units': 0,
                'Error': 'No Ventrata data found for this booking'
            }]
        
        # If update file provided, check for ID matching
        if self.update_df is not None:
            return self._process_with_update_file(order_ref, norm_ref, ventrata_rows, booking_data)
        
        # No update file: process normally
        return self._process_booking_normal(order_ref, norm_ref, ventrata_rows, booking_data)
    
    def _identify_extractor_type(self, reseller):
        """
        Identify which extractor to use based on reseller.
        
        For GYG platforms (including MDA), returns 'gyg_standard' since
        we always try GYG Standard first, then fall back to MDA if needed.
        
        Args:
            reseller: Reseller name string
            
        Returns:
            str: 'gyg_standard', 'gyg_mda', or 'non_gyg'
        """
        if pd.isna(reseller) or not reseller:
            return 'non_gyg'
        
        reseller_str = str(reseller)
        
        # Check if it's ANY GYG platform (including MDA)
        # We'll use fallback logic: try GYG Standard first, then GYG MDA
        if any(gyg in reseller_str for gyg in ['GetYourGuide', 'Get your Guide']):
            return 'gyg_standard'  # This triggers the fallback logic
        
        # Default to non-GYG
        return 'non_gyg'
    
    def _build_update_id_mapping(self):
        """Build a mapping from Ventrata ID to update file row for quick lookup."""
        self.update_id_map = {}
        
        if self.update_df is None:
            return
        
        id_col = self.update_col_map.get('id')
        if not id_col:
            logger.warning("Update file missing ID column, cannot build ID mapping")
            return
        
        for idx, row in self.update_df.iterrows():
            ventrata_id = row[id_col]
            if pd.notna(ventrata_id) and ventrata_id != '':
                self.update_id_map[ventrata_id] = row
        
        logger.debug(f"Built update ID mapping with {len(self.update_id_map)} entries")
    
    def _validate_travel_dates(self):
        """
        Validate that travel dates in Ventrata and Update file match.
        
        This ensures the user doesn't accidentally use an update file from a different
        date with a new Ventrata file. Both files must have the same travel date(s).
        
        Raises:
            ValueError: If travel dates don't match between Ventrata and Update file
        """
        if self.update_df is None:
            return
        
        # Get travel date column from Ventrata
        ventrata_travel_date_col = self.ventrata_col_map.get('travel date')
        if not ventrata_travel_date_col:
            # Try prefixed version (when merged with Monday)
            ventrata_travel_date_col = self.ventrata_col_map.get('ventrata_travel date')
        
        if not ventrata_travel_date_col or ventrata_travel_date_col not in self.ventrata_df.columns:
            logger.warning("Ventrata file missing Travel Date column, skipping date validation")
            return
        
        # Get travel date column from Update file
        update_travel_date_col = self.update_col_map.get('travel date')
        if not update_travel_date_col or update_travel_date_col not in self.update_df.columns:
            logger.warning("Update file missing Travel Date column, skipping date validation")
            return
        
        # Get unique normalized travel dates from Ventrata
        ventrata_dates = set()
        for date_val in self.ventrata_df[ventrata_travel_date_col].dropna().unique():
            normalized = normalize_travel_date(date_val)
            logger.debug(f"Ventrata date: '{date_val}' (type: {type(date_val).__name__}) -> normalized: '{normalized}'")
            if normalized:
                ventrata_dates.add(normalized)
        
        # Get unique normalized travel dates from Update file
        update_dates = set()
        for date_val in self.update_df[update_travel_date_col].dropna().unique():
            normalized = normalize_travel_date(date_val)
            logger.debug(f"Update date: '{date_val}' (type: {type(date_val).__name__}) -> normalized: '{normalized}'")
            if normalized:
                update_dates.add(normalized)
        
        logger.info(f"Ventrata travel dates: {sorted(ventrata_dates)}")
        logger.info(f"Update file travel dates: {sorted(update_dates)}")
        
        # Check if there's any overlap
        if not ventrata_dates:
            logger.warning("No valid travel dates found in Ventrata file")
            return
        
        if not update_dates:
            logger.warning("No valid travel dates found in Update file")
            return
        
        # Check if dates match (at least one common date must exist)
        common_dates = ventrata_dates & update_dates
        
        if not common_dates:
            # No matching dates - this is an error!
            error_msg = (
                f"Travel date mismatch between Ventrata and Update file!\n"
                f"Ventrata file contains dates: {sorted(ventrata_dates)}\n"
                f"Update file contains dates: {sorted(update_dates)}\n"
                f"The Update file must be from the same travel date as the Ventrata file."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Travel date validation passed. Common dates: {sorted(common_dates)}")
    
    def _extract_travel_date(self, ventrata_row, monday_row=None, order_ref='Unknown'):
        """
        Extract Travel Date from Ventrata data ONLY.
        
        When Ventrata and Monday are merged, "Travel Date" becomes "ventrata_Travel Date".
        This method handles both scenarios (merged and non-merged).
        
        Args:
            ventrata_row: Ventrata DataFrame row
            monday_row: Optional Monday DataFrame row (not used, kept for backward compatibility)
            order_ref: Order reference for logging
            
        Returns:
            Travel Date value (datetime, string, or None)
        """
        travel_date = None
        
        # Try to find Travel Date column in Ventrata data
        # Check both unprefixed and prefixed versions (handles merged and non-merged scenarios)
        
        # Option 1: Try unprefixed 'travel date' (Ventrata-only scenario)
        ventrata_col = self.ventrata_col_map.get('travel date')
        if ventrata_col and ventrata_col in ventrata_row.index:
            travel_date_val = ventrata_row[ventrata_col]
            if not pd.isna(travel_date_val):
                travel_date = travel_date_val
                logger.debug(f"Travel Date for {order_ref} extracted from Ventrata (unprefixed): {travel_date}")
                return travel_date
        
        # Option 2: Try prefixed 'ventrata_travel date' (Ventrata+Monday merged scenario)
        ventrata_prefixed_col = self.ventrata_col_map.get('ventrata_travel date')
        if ventrata_prefixed_col and ventrata_prefixed_col in ventrata_row.index:
            travel_date_val = ventrata_row[ventrata_prefixed_col]
            if not pd.isna(travel_date_val):
                travel_date = travel_date_val
                logger.debug(f"Travel Date for {order_ref} extracted from Ventrata (prefixed): {travel_date}")
                return travel_date
        
        # Not found in either format
        logger.warning(f"Travel Date not found for {order_ref} in Ventrata data. "
                      f"Checked columns: {ventrata_col}, {ventrata_prefixed_col}")
        
        return travel_date
    
    def _format_travel_date_for_output(self, travel_date):
        """
        Format travel date for output display.
        
        Args:
            travel_date: Travel date value (datetime, string, or None)
            
        Returns:
            str: Formatted date string in YYYY-MM-DD format, or empty string
        """
        if travel_date is None or pd.isna(travel_date):
            return ''
        
        try:
            if isinstance(travel_date, pd.Timestamp):
                return travel_date.strftime('%Y-%m-%d')
            elif isinstance(travel_date, str):
                # Try to parse and reformat
                parsed = pd.to_datetime(travel_date)
                return parsed.strftime('%Y-%m-%d')
            else:
                return str(travel_date)
        except Exception as e:
            logger.warning(f"Error formatting travel date {travel_date}: {e}")
            return str(travel_date) if travel_date else ''
    
    def _build_booking_data_dict(self, row, monday_row=None):
        """
        Build booking data dict from a Ventrata row.
        
        Args:
            row: Ventrata DataFrame row
            monday_row: Optional Monday DataFrame row (not used for travel_date, kept for future use)
            
        Returns:
            dict: Booking data including travel_date from Ventrata only
        """
        # Extract travel_date from Ventrata only (handles both merged and non-merged scenarios)
        travel_date = self._extract_travel_date(row, monday_row=None, order_ref='building_data_dict')
        
        return {
            'first_name': get_column_value(row, self.ventrata_col_map, 'ticket customer first name', 'first name'),
            'last_name': get_column_value(row, self.ventrata_col_map, 'ticket customer last name', 'last name'),
            'customer': get_column_value(row, self.ventrata_col_map, 'customer'),
            'travel_date': travel_date,
            'product_code': get_column_value(row, self.ventrata_col_map, 'product code'),
            'product_tags': get_column_value(row, self.ventrata_col_map, 'product tags'),
            'unit': get_column_value(row, self.ventrata_col_map, 'unit'),
        }

    @staticmethod
    def _is_colosseum_product(product_tags):
        """Check if product tags indicate a Colosseum product."""
        if product_tags is None or (isinstance(product_tags, float) and pd.isna(product_tags)):
            return False
        
        tags_str = str(product_tags).lower()
        colosseum_keywords = ['colosseum', 'colosseo', 'kolosseum', 'colisée']
        return any(keyword in tags_str for keyword in colosseum_keywords)
    
    def _assign_unit_types(self, travelers, unit_counts, product_tags, customer_country, is_gyg):
        """
        Assign unit types to travelers based on ages and available units.
        
        Assignment logic:
        1. Sort travelers from youngest to oldest
        2. If Child units exist: Assign Child/Infant to under-18 travelers (youngest first)
           - Use product tags to determine Child vs Infant conversion
        3. If Youth units exist:
           - Non-GYG: Keep as Youth (preserve booking)
           - GYG EU: Keep as Youth (preserve booking, validation flags errors if age outside 18-24)
           - GYG non-EU: Convert Youth based on age (mark for faded yellow coloring)
             * If age < 18: Convert to Child
             * If age >= 18: Convert to Adult
        4. If Adult units exist: Assign Adult to remaining travelers
        
        Units must be present in the booking to be assigned.
        Age restrictions are enforced during assignment.
        
        Args:
            travelers: List of traveler dicts with age info
            unit_counts: Dict of unit type counts
            product_tags: Product tags for Infant->Child conversion
            customer_country: Customer country for EU/non-EU determination
            is_gyg: Whether this is a GYG booking
            
        Returns:
            list: Travelers with 'unit_type' assigned
        """
        # Sort by age (youngest first)
        def safe_get_age(traveler):
            age = traveler.get('age')
            if age is None:
                return 100  # Put travelers without age at end
            return float(age)
        
        sorted_travelers = sorted(travelers, key=safe_get_age)
        
        # Get unit counts
        child_units = unit_counts.get('Child', 0) + unit_counts.get('Infant', 0)
        infant_units = unit_counts.get('Infant', 0)
        youth_units = unit_counts.get('Youth', 0)
        adult_units = unit_counts.get('Adult', 0)
        
        # Check if EU country
        is_eu = is_eu_country(customer_country)
        
        # Initialize all travelers as unassigned
        for traveler in sorted_travelers:
            traveler['unit_type'] = None
            traveler['original_unit_type'] = None  # For ID matching before conversions
            traveler['youth_converted_to_adult'] = False  # Flag for coloring
        
        # Step 1: Assign Child/Infant units (only if Child units exist in booking)
        if child_units > 0:
            child_assigned = 0
            infant_assigned = 0
            for traveler in sorted_travelers:
                age = traveler.get('age')
                # Only assign Child/Infant to travelers under 18
                if age is not None and age < 18 and child_assigned < child_units:
                    if infant_assigned < infant_units:
                        base_unit = 'Infant'
                        infant_assigned += 1
                    else:
                        base_unit = 'Child'
                    # Store original unit type for ID matching (BEFORE conversion)
                    traveler['original_unit_type'] = base_unit
                    # Check if should be converted from Infant based on monument
                    traveler['unit_type'] = convert_infant_to_child_for_colosseum(base_unit, product_tags)
                    child_assigned += 1
        
        # Step 2: Assign Youth units (only if Youth units exist in booking)
        if youth_units > 0:
            youth_assigned = 0
            
            for traveler in sorted_travelers:
                if traveler.get('unit_type') is not None:
                    continue  # Already assigned
                
                age = traveler.get('age')
                
                # Rule 1: Non-GYG bookings - Keep Youth as booked
                if not is_gyg:
                    if youth_assigned < youth_units:
                        traveler['original_unit_type'] = 'Youth'  # Store original for ID matching
                        traveler['unit_type'] = 'Youth'
                        youth_assigned += 1
                        logger.debug(f"Non-GYG: Keeping Youth unit for {traveler.get('name')}")
                
                # Rule 2: GYG EU bookings - Keep Youth as booked (preserve unit type)
                # Validation will flag errors if age is outside 18-24 range
                elif is_gyg and is_eu:
                    if youth_assigned < youth_units:
                        traveler['original_unit_type'] = 'Youth'  # Store original for ID matching
                        traveler['unit_type'] = 'Youth'
                        youth_assigned += 1
                        if age is not None and 18 <= age < 25:
                            logger.debug(f"GYG EU: Assigning Youth for {traveler.get('name')}, age {age} (valid range)")
                        else:
                            logger.debug(f"GYG EU: Keeping Youth for {traveler.get('name')}, age {age} (outside range, will flag error)")
                
                # Rule 3: GYG non-EU bookings - Convert Youth based on age (mark for coloring)
                # If age < 18: Convert to Child
                # If age >= 18: Convert to Adult
                elif is_gyg and not is_eu:
                    if youth_assigned < youth_units:
                        # Store original unit type as Youth BEFORE conversion
                        traveler['original_unit_type'] = 'Youth'
                        
                        # Convert based on age
                        if age is not None and age < 18:
                            base_unit = 'Child'
                            traveler['unit_type'] = convert_infant_to_child_for_colosseum(base_unit, product_tags)
                            traveler['youth_converted_to_adult'] = True  # Flag for coloring (reusing for any conversion)
                            youth_assigned += 1
                            logger.info(f"GYG non-EU: Converting Youth to Child for {traveler.get('name')}, age {age} (country: {customer_country})")
                        else:
                            # Age >= 18 or age unknown
                            traveler['unit_type'] = 'Adult'
                            traveler['youth_converted_to_adult'] = True  # Flag for coloring
                            youth_assigned += 1
                            logger.info(f"GYG non-EU: Converting Youth to Adult for {traveler.get('name')}, age {age} (country: {customer_country})")
        
        # Step 3: Assign Adult units (only if Adult units exist in booking)
        if adult_units > 0:
            adult_assigned = 0
            for traveler in sorted_travelers:
                # Assign Adult to remaining unassigned travelers
                if traveler.get('unit_type') is None and adult_assigned < adult_units:
                    traveler['original_unit_type'] = 'Adult'  # Store original for ID matching
                    traveler['unit_type'] = 'Adult'
                    adult_assigned += 1
        
        # Warning for any unassigned travelers (likely due to missing age data or unit count mismatch)
        for traveler in sorted_travelers:
            if traveler.get('unit_type') is None:
                age = traveler.get('age')
                name = traveler.get('name', 'Unknown')
                if age is None:
                    # No age data - can't determine unit type, assign based on available units
                    logger.warning(f"No age data for {name}, cannot determine unit type from age")
                    # Assign based on what units are available, prioritizing Adult
                    if adult_units > 0:
                        traveler['original_unit_type'] = 'Adult'
                        traveler['unit_type'] = 'Adult'
                    elif child_units > 0:
                        traveler['original_unit_type'] = 'Child'
                        traveler['unit_type'] = 'Child'
                    elif youth_units > 0:
                        traveler['original_unit_type'] = 'Youth'
                        traveler['unit_type'] = 'Youth'
                    else:
                        # No units available at all - default to Adult
                        traveler['original_unit_type'] = 'Adult'
                        traveler['unit_type'] = 'Adult'
                else:
                    # Has age but wasn't assigned - unit count mismatch
                    logger.warning(f"Unit type not assigned for {name} (age {age:.1f}) - unit count mismatch")
                    # Assign based on age as fallback
                    if age < 18:
                        traveler['original_unit_type'] = 'Child'
                        traveler['unit_type'] = 'Child'
                    elif 18 <= age < 25:
                        traveler['original_unit_type'] = 'Youth'
                        traveler['unit_type'] = 'Youth'
                    else:
                        traveler['original_unit_type'] = 'Adult'
                        traveler['unit_type'] = 'Adult'
        
        return sorted_travelers
    
    def _map_travelers_to_ids(self, travelers, ventrata_rows, order_ref):
        """
        Map GYG travelers to Ventrata row IDs by ORIGINAL unit type (before conversions).
        
        Travelers are matched to Ventrata rows based on original_unit_type,
        in the order they appear. This ensures correct matching even after
        unit type conversions (e.g., Youth -> Adult for non-EU, Infant -> Child for Colosseum).
        
        Args:
            travelers: List of traveler dicts with unit_type and original_unit_type
            ventrata_rows: DataFrame with Ventrata rows for this booking
            order_ref: Order reference for logging
            
        Returns:
            list: Travelers with 'ventrata_id' added
        """
        id_col = self.ventrata_col_map.get('id')
        unit_col = self.ventrata_col_map.get('unit')
        
        if not id_col or id_col not in ventrata_rows.columns:
            # No ID column, assign empty IDs
            for traveler in travelers:
                traveler['ventrata_id'] = ''
            return travelers
        
        # Group travelers by ORIGINAL unit type (preserve order within each unit)
        # Use original_unit_type to match with Ventrata's unit types (before conversions)
        unit_to_travelers = {}
        for traveler in travelers:
            # Use original_unit_type for matching (falls back to unit_type if not set)
            unit_type = traveler.get('original_unit_type') or traveler.get('unit_type', 'Unknown')
            if unit_type not in unit_to_travelers:
                unit_to_travelers[unit_type] = []
            unit_to_travelers[unit_type].append(traveler)
        
        # Track which traveler index to use for each unit type
        unit_traveler_idx = {unit: 0 for unit in unit_to_travelers.keys()}
        
        # Process Ventrata rows in order and assign IDs to travelers
        for _, row in ventrata_rows.iterrows():
            unit_type = str(row[unit_col]).strip() if unit_col and unit_col in row.index else 'Unknown'
            ventrata_id = row[id_col] if id_col and id_col in row.index else ''
            
            # Try to find matching traveler by unit type
            # For Infant units in Ventrata, first try 'Infant', then fall back to 'Child'
            # (travelers might have original_unit_type as either)
            matching_unit_types = [unit_type]
            if unit_type == 'Infant':
                matching_unit_types.append('Child')  # Fallback for Colosseum conversions
            elif unit_type == 'Child':
                matching_unit_types.append('Infant')  # Also check Infant travelers
            
            matched = False
            for matching_unit_type in matching_unit_types:
                if matching_unit_type in unit_to_travelers:
                    idx = unit_traveler_idx.get(matching_unit_type, 0)
                    travelers_for_unit = unit_to_travelers[matching_unit_type]
                    
                    if idx < len(travelers_for_unit):
                        travelers_for_unit[idx]['ventrata_id'] = ventrata_id
                        unit_traveler_idx[matching_unit_type] = idx + 1
                        matched = True
                        break
            
            if not matched:
                logger.debug(f"No traveler found for unit type {unit_type} in {order_ref}")
        
        # Assign empty IDs to any unmatched travelers
        for unit_type, travelers_list in unit_to_travelers.items():
            for traveler in travelers_list:
                if 'ventrata_id' not in traveler:
                    traveler['ventrata_id'] = ''
        
        logger.debug(f"Mapped {len(travelers)} GYG travelers to IDs for {order_ref}")
        
        return travelers
    
    def _process_with_update_file(self, order_ref, norm_ref, ventrata_rows, booking_data):
        """
        Process booking with update file support.
        
        Strategy:
        1. Get all IDs from Ventrata for this booking
        2. Check which IDs exist in update file
        3. For existing IDs: Reuse name and unit type, update notes
        4. For new IDs: Extract names normally
        5. Validate ID counts match between update file and Ventrata (by Order Reference)
        
        Args:
            order_ref: Original order reference
            norm_ref: Normalized order reference
            ventrata_rows: DataFrame with Ventrata rows
            booking_data: Dict with booking info
            
        Returns:
            list: List of result dicts
        """
        id_col = self.ventrata_col_map.get('id')
        if not id_col or id_col not in ventrata_rows.columns:
            logger.warning(f"No ID column in Ventrata for {order_ref}, falling back to normal extraction")
            return self._process_booking_normal(order_ref, norm_ref, ventrata_rows, booking_data)
        
        # Get all IDs from Ventrata for this booking
        ventrata_ids = []
        for _, row in ventrata_rows.iterrows():
            v_id = row[id_col]
            if pd.notna(v_id) and v_id != '':
                ventrata_ids.append(v_id)
        
        if not ventrata_ids:
            logger.warning(f"No valid IDs found in Ventrata for {order_ref}")
            return self._process_booking_normal(order_ref, norm_ref, ventrata_rows, booking_data)
        
        # Split IDs into existing (in update file) and new
        existing_ids = []
        new_ids = []
        for v_id in ventrata_ids:
            if v_id in self.update_id_map:
                existing_ids.append(v_id)
            else:
                new_ids.append(v_id)
        
        logger.debug(f"{order_ref}: {len(existing_ids)} existing IDs, {len(new_ids)} new IDs")
        
        # Validate: Check if Order Reference in update file has same number of IDs as Ventrata
        validation_passed = True
        if existing_ids:
            # Get all update file rows for this Order Reference
            update_order_ref_col = self.update_col_map.get('order reference')
            update_id_col = self.update_col_map.get('id')
            
            if update_order_ref_col and update_id_col:
                update_rows_for_booking = self.update_df[
                    self.update_df['_normalized_order_ref'] == norm_ref
                ]
                
                if not update_rows_for_booking.empty:
                    # Get IDs from update file for this booking
                    update_ids_for_booking = []
                    for _, row in update_rows_for_booking.iterrows():
                        u_id = row[update_id_col]
                        if pd.notna(u_id) and u_id != '':
                            update_ids_for_booking.append(u_id)
                    
                    # Check if IDs match exactly
                    ventrata_ids_set = set(ventrata_ids)
                    update_ids_set = set(update_ids_for_booking)
                    
                    if ventrata_ids_set != update_ids_set:
                        logger.warning(f"ID mismatch for {order_ref}: Ventrata IDs {ventrata_ids_set} vs Update IDs {update_ids_set}")
                        validation_passed = False
        
        # If validation failed, re-extract everything
        if not validation_passed:
            logger.info(f"Re-extracting {order_ref} due to ID mismatch")
            results = self._process_booking_normal(order_ref, norm_ref, ventrata_rows, booking_data)
            # Add error flag to all results
            for result in results:
                existing_error = result.get('Error', '')
                mismatch_error = "Information does not match with update file"
                if existing_error:
                    result['Error'] = existing_error + ' | ' + mismatch_error
                else:
                    result['Error'] = mismatch_error
                    result['_highlight_yellow'] = True  # Flag for yellow highlighting
            return results
        
        # Build results by combining existing and new data
        results = []
        
        # Process existing IDs: Reuse from update file
        for v_id in existing_ids:
            update_row = self.update_id_map[v_id]
            ventrata_row_for_id = ventrata_rows[ventrata_rows[id_col] == v_id].iloc[0]
            
            # Public Notes should reflect latest Ventrata info
            public_notes_col = self.ventrata_col_map.get('public notes')
            public_notes = str(ventrata_row_for_id[public_notes_col]) if public_notes_col and public_notes_col in ventrata_row_for_id.index else ''
            
            # Private Notes should reflect the update file (manual edits)
            update_private_notes_col = self.update_col_map.get('private notes')
            if update_private_notes_col and update_private_notes_col in update_row.index:
                value = update_row[update_private_notes_col]
                private_notes = '' if pd.isna(value) else str(value)
            else:
                private_notes_col = self.ventrata_col_map.get('private notes')
                private_notes = str(ventrata_row_for_id[private_notes_col]) if private_notes_col and private_notes_col in ventrata_row_for_id.index else ''
            
            # Build result from update file data + preserved notes
            full_name_col = self.update_col_map.get('full name')
            unit_type_col = self.update_col_map.get('unit type')
            
            # Copy fields from Ventrata first
            first_row = ventrata_rows.iloc[0]
            travel_date_raw = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)
            travel_date = self._format_travel_date_for_output(travel_date_raw)
            
            total_units = len(ventrata_rows)
            
            product_code_col = self.ventrata_col_map.get('product code')
            product_code = first_row[product_code_col] if product_code_col else ''

            product_tags_col = self.ventrata_col_map.get('product tags')
            product_tags = first_row[product_tags_col] if product_tags_col else ''
            product_tags_str = str(product_tags) if product_tags is not None else ''
            is_colosseum_booking = self._is_colosseum_product(product_tags)
            tag_options = get_tag_options(product_code, product_tags_str)
            
            tour_time_col = self.ventrata_col_map.get('tour time')
            tour_time = normalize_time(first_row[tour_time_col]) if tour_time_col else ''
            
            language = extract_language_from_product_code(product_code)
            tour_type = extract_tour_type_from_product_code(product_code)
            
            # Special handling for Gold Hour / Twilight product
            if product_code == 'ROMARNEVEENG':
                language = 'Gold Hour / Twilight'
            
            reseller_col = self.ventrata_col_map.get('reseller')
            reseller = str(first_row[reseller_col]) if reseller_col and reseller_col in first_row.index else ''
            
            result = {
                'Travel Date': travel_date,
                'Order Reference': order_ref,
                'Full Name': update_row[full_name_col] if full_name_col else '',
                'Unit Type': update_row[unit_type_col] if unit_type_col else '',
                'Total Units': total_units,
                'Tour Time': tour_time,
                'Language': language,
                'Tour Type': tour_type,
                'Public Notes': public_notes,
                'Private Notes': private_notes,
            }

            # Helper function to get value from update file
            def get_update_value(col_name_lower):
                """Get value from update file row, return empty string if not found or NaN."""
                col = self.update_col_map.get(col_name_lower)
                if col and col in update_row.index:
                    val = update_row[col]
                    if pd.notna(val) and str(val).strip():
                        return str(val).strip()
                return ''
            
            # Get Tag value from update file
            tag_value = get_update_value('tag')
            
            if is_colosseum_booking:
                # Get these values from update file (preserve manual edits)
                result.update({
                    'Change By': get_update_value('change by'),
                    'PNR': get_update_value('pnr'),
                    'Ticket Group': get_update_value('ticket group'),
                    'Codice': get_update_value('codice'),
                    'Sigilo': get_update_value('sigilo'),
                })
            
            result.update({
                'Product Code': product_code,
                'Tag': tag_value,  # Preserve Tag from update file
                'ID': v_id,
                'Reseller': reseller,
                'Error': '',
                '_youth_converted': False,
                '_from_update': True,  # Internal flag
                '_tag_options': tag_options,
            })

            # Add Monday columns if applicable (but don't overwrite update file values)
            monday_row = booking_data.get('monday_row') if isinstance(booking_data, dict) else None
            if is_colosseum_booking and should_include_monday_columns(self.scenario) and monday_row is not None:
                # Only use Monday values if update file didn't have them
                if not result.get('PNR'):
                    pnr_col = self.monday_col_map.get('ticket pnr') or self.monday_col_map.get('Ticket PNR')
                    if not pnr_col:
                        for col_name in monday_row.index:
                            if 'pnr' in str(col_name).lower():
                                pnr_col = col_name
                                break
                    
                    pnr_value = ''
                    if pnr_col and pnr_col in monday_row:
                        pnr_value = monday_row[pnr_col] if not pd.isna(monday_row[pnr_col]) else ''
                    result['PNR'] = pnr_value
                
                if not result.get('Ticket Group'):
                    ticket_group_col = self.monday_col_map.get('ticket group')
                    ticket_group_value = ''
                    if ticket_group_col and ticket_group_col in monday_row:
                        ticket_group_value = monday_row[ticket_group_col] if not pd.isna(monday_row[ticket_group_col]) else ''
                    result['Ticket Group'] = ticket_group_value
                
                # Generate TIX NOM from PNR if we have one
                if result.get('PNR'):
                    result['TIX NOM'] = generate_tix_nom(result['PNR'])
                else:
                    result['TIX NOM'] = ''
            
            results.append(result)
        
        # Process new IDs: Extract normally
        if new_ids:
            logger.info(f"Extracting {len(new_ids)} new travelers for {order_ref}")
            
            # Get preserved values from update file for this booking (from existing IDs)
            # These values are typically the same for all rows in a booking
            booking_preserved_values = {}
            if existing_ids:
                first_existing_id = existing_ids[0]
                first_update_row = self.update_id_map[first_existing_id]
                
                # Columns to preserve from update file for new IDs in same booking
                preserve_cols = ['tag', 'pnr', 'change by', 'ticket group', 'codice', 'sigilo']
                for col_name in preserve_cols:
                    col = self.update_col_map.get(col_name)
                    if col and col in first_update_row.index:
                        val = first_update_row[col]
                        if pd.notna(val) and str(val).strip():
                            # Map to result column names
                            result_col_name = {
                                'tag': 'Tag',
                                'pnr': 'PNR',
                                'change by': 'Change By',
                                'ticket group': 'Ticket Group',
                                'codice': 'Codice',
                                'sigilo': 'Sigilo'
                            }.get(col_name, col_name)
                            booking_preserved_values[result_col_name] = str(val).strip()
            
            # Filter ventrata_rows to only new IDs
            new_ventrata_rows = ventrata_rows[ventrata_rows[id_col].isin(new_ids)]
            
            # Extract names for new IDs
            new_results = self._process_booking_normal(order_ref, norm_ref, new_ventrata_rows, booking_data)
            
            # Apply preserved values from update file to new results
            if booking_preserved_values:
                for new_result in new_results:
                    for col_name, value in booking_preserved_values.items():
                        # Only apply if the result doesn't already have a value
                        if not new_result.get(col_name):
                            new_result[col_name] = value
            
            results.extend(new_results)
        
        return results
    
    def _process_booking_normal(self, order_ref, norm_ref, ventrata_rows, booking_data):
        """
        Normal booking processing without update file (original logic).
        
        Args:
            order_ref: Original order reference
            norm_ref: Normalized order reference
            ventrata_rows: DataFrame with Ventrata rows
            booking_data: Dict with booking info
            
        Returns:
            list: List of result dicts
        """
        # This is the original _process_booking logic (lines 354-650)
        # Get booking info
        first_row = ventrata_rows.iloc[0]
        reseller_col = self.ventrata_col_map.get('reseller')
        reseller = str(first_row[reseller_col]) if reseller_col and reseller_col in first_row else ''
        
        # Identify extractor type
        extractor_type = self._identify_extractor_type(reseller)
        
        logger.debug(f"Processing order {order_ref} with {extractor_type} extractor")
        
        # Extract travelers
        public_notes_col = self.ventrata_col_map.get('public notes')
        public_notes = str(first_row[public_notes_col]) if public_notes_col else ''
        
        private_notes_col = self.ventrata_col_map.get('private notes')
        private_notes = str(first_row[private_notes_col]) if private_notes_col else ''
        
        # Build booking data dict for all extractors (includes travel_date for age calculation)
        # Get monday_row from the passed booking_data parameter
        monday_row = booking_data.get('monday_row') if isinstance(booking_data, dict) else None
        
        # Build booking data dict with both Ventrata and Monday data
        booking_data = self._build_booking_data_dict(first_row, monday_row)
        
        # Preserve monday_row in booking_data for later use
        if monday_row is not None:
            booking_data['monday_row'] = monday_row
        
        travel_date_raw = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)

        # For non-GYG, pass booking data for structured column access
        if extractor_type == 'non_gyg':
            # Need to process each row separately for non-GYG
            travelers = []
            id_col = self.ventrata_col_map.get('id')
            
            if not id_col:
                logger.warning(f"ID column not found in Ventrata file for {order_ref}")
            
            for _, row in ventrata_rows.iterrows():
                # Build booking data with Monday row if available
                row_booking_data = self._build_booking_data_dict(row, monday_row)
                row_travelers = self.extractors['non_gyg'].extract_travelers(public_notes, order_ref, row_booking_data)
                
                # Add Ventrata ID to each traveler (non-GYG: 1-to-1 mapping)
                if id_col and id_col in row.index:
                    ventrata_id = row[id_col]
                else:
                    ventrata_id = ''
                    if id_col:
                        logger.debug(f"ID column '{id_col}' not in row for {order_ref}")
                
                for traveler in row_travelers:
                    traveler['ventrata_id'] = ventrata_id
                
                travelers.extend(row_travelers)
            
            # If non-GYG extraction failed (empty structured fields), use private notes template
            if not travelers:
                unit_col = self.ventrata_col_map.get('unit')
                travelers, missing_units = build_travelers_from_private_notes(private_notes, ventrata_rows, unit_col, travel_date_raw)
                if travelers:
                    if missing_units:
                        self.bookings_require_unit_check.add(norm_ref)
                    logger.info(f"Private notes template extracted {len(travelers)} travelers for {order_ref}")
                else:
                    logger.warning(f"Non-GYG structured extraction failed for {order_ref}, no names found")
        
        elif extractor_type in ['gyg_standard', 'gyg_mda']:
            # For ALL GYG bookings: Try GYG Standard first, fall back to GYG MDA if it fails
            logger.debug(f"Trying GYG Standard extraction first for order {order_ref}")
            travelers = self.extractors['gyg_standard'].extract_travelers(public_notes, order_ref, booking_data)
            
            if not travelers:
                # GYG Standard failed, fall back to GYG MDA patterns
                logger.info(f"GYG Standard extraction failed for {order_ref}, falling back to GYG MDA patterns")
                travelers = self.extractors['gyg_mda'].extract_travelers(public_notes, order_ref, booking_data)
                
                if not travelers:
                    # Both GYG Standard and MDA failed; try private notes parser
                    logger.warning(f"All extraction methods failed for GYG order {order_ref}, using private notes template")
                    unit_col = self.ventrata_col_map.get('unit')
                    travelers, missing_units = build_travelers_from_private_notes(private_notes, ventrata_rows, unit_col, travel_date_raw)
                    if travelers:
                        if missing_units:
                            self.bookings_require_unit_check.add(norm_ref)
                        logger.info(f"Private notes template extracted {len(travelers)} travelers for {order_ref}")
                else:
                    logger.info(f"GYG MDA fallback successful for {order_ref}: extracted {len(travelers)} travelers")
            else:
                logger.debug(f"GYG Standard extraction successful for {order_ref}: extracted {len(travelers)} travelers")
            
            # For GYG bookings: supplement/replace missing DOBs from private notes if available
            # This helps with unit type assignment when DOBs are missing in public notes
            if travelers:
                unit_col = self.ventrata_col_map.get('unit')
                travelers = supplement_travelers_with_private_notes(
                    travelers, private_notes, travel_date_raw, ventrata_rows, unit_col
                )
        
        else:
            # Fallback for any other extractor type
            extractor = self.extractors.get(extractor_type)
            if extractor:
                travelers = extractor.extract_travelers(public_notes, order_ref, booking_data)
            else:
                travelers = []
        
        # Sort travelers alphabetically within this booking (A-Z)
        if travelers:
            travelers.sort(key=lambda t: t.get('name', '').lower())
            logger.debug(f"Sorted {len(travelers)} travelers alphabetically for {order_ref}")
        
        # Get pre-computed errors
        pre_computed_errors = self.booking_errors_cache.get(norm_ref, [])
        
        # Get booking-level info
        total_units = len(ventrata_rows)
        
        # Extract travel_date from Ventrata only (handles both merged and non-merged scenarios)
        travel_date = travel_date_raw
        
        # Get tour info
        product_code_col = self.ventrata_col_map.get('product code')
        product_code = first_row[product_code_col] if product_code_col else ''
        
        tour_time_col = self.ventrata_col_map.get('tour time')
        tour_time = normalize_time(first_row[tour_time_col]) if tour_time_col else ''
        
        language = extract_language_from_product_code(product_code)
        tour_type = extract_tour_type_from_product_code(product_code)
        
        product_tags_col = self.ventrata_col_map.get('product tags')
        product_tags = first_row[product_tags_col] if product_tags_col else ''
        is_colosseum_booking = self._is_colosseum_product(product_tags)
        product_tags_str = str(product_tags) if product_tags is not None else ''
        tag_options = get_tag_options(product_code, product_tags_str)
        
        # Get customer country and platform info for youth handling
        customer_country_col = self.ventrata_col_map.get('customer country')
        customer_country = first_row[customer_country_col] if customer_country_col else ''
        is_gyg = extractor_type in ['gyg_standard', 'gyg_mda']
        
        # Assign unit types if we have travelers
        if travelers:
            unit_col = self.ventrata_col_map.get('unit')
            unit_counts = get_unit_counts(ventrata_rows, unit_col) if unit_col else {}
            
            if extractor_type != 'non_gyg':
                # Check if unit types are already assigned (e.g., by fallback extractors)
                has_unit_types = all(t.get('unit_type') is not None for t in travelers)
                
                if not has_unit_types:
                    # Assign unit types based on ages, unit counts, country, and platform
                    travelers = self._assign_unit_types(
                        travelers, 
                        unit_counts, 
                        product_tags_str, 
                        customer_country, 
                        is_gyg
                    )
                else:
                    logger.debug(f"Unit types already assigned for {order_ref}, skipping assignment")
            
            # For GYG: Map travelers to Ventrata row IDs by unit type (requires unit_type)
            # ID mapping must happen BEFORE Infant->Child conversion to match Ventrata's unit types
            if extractor_type in ['gyg_standard', 'gyg_mda']:
                travelers = self._map_travelers_to_ids(travelers, ventrata_rows, order_ref)
            
            # Convert Infant to Child for Colosseum product tags (all resellers)
            # This happens AFTER ID mapping to avoid mismatches
            if product_tags_str:
                for traveler in travelers:
                    unit_type = traveler.get('unit_type')
                    if unit_type:
                        converted = convert_infant_to_child_for_colosseum(unit_type, product_tags_str)
                        if converted != unit_type:
                            traveler['unit_type'] = converted
                            logger.debug(f"Converted {unit_type} to {converted} for Colosseum booking")
        
        # Check for youth validation (EU countries only)
        unit_col = self.ventrata_col_map.get('unit')
        unit_counts = get_unit_counts(ventrata_rows, unit_col) if unit_col else {}
        
        youth_errors = validate_youth_booking(travelers, unit_counts, customer_country, is_gyg)
        
        # Build results for each traveler
        results = []
        if travelers:
            for traveler in travelers:
                # Aggregate all errors
                traveler_errors = list(pre_computed_errors)  # Copy pre-computed errors
                
                # Add youth errors (but not if Youth was converted to Adult for non-EU)
                # Non-EU Youth conversion should not flag errors
                if not traveler.get('youth_converted_to_adult', False):
                    traveler_errors.extend(youth_errors)
                
                # Check name content
                if name_has_forbidden_issue(traveler['name']):
                    traveler_errors.append("Please Check Names before Insertion")
                
                # Get Travel Date for output (from Ventrata only)
                travel_date_raw = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)
                travel_date = self._format_travel_date_for_output(travel_date_raw)
                
                # Special handling for Gold Hour / Twilight product
                if product_code == 'ROMARNEVEENG':
                    language = 'Gold Hour / Twilight'
                
                # Build result dict with reordered columns
                result = {
                    'Travel Date': travel_date,
                    'Order Reference': order_ref,
                    'Full Name': traveler['name'],
                    'Unit Type': traveler.get('unit_type', ''),
                    'Total Units': total_units,
                    'Tour Time': tour_time,
                    'Language': language,
                    'Tour Type': tour_type,
                    'Private Notes': private_notes,
                }

                if is_colosseum_booking:
                    result.update({
                        'Change By': '',
                        'PNR': '',
                        'Ticket Group': '',
                        'Codice': '',
                        'Sigilo': '',
                    })

                result.update({
                    'Product Code': product_code,
                    'Tag': '',
                    'ID': traveler.get('ventrata_id', ''),
                    'Reseller': reseller,
                    'Error': ' | '.join(traveler_errors) if traveler_errors else '',
                    '_youth_converted': traveler.get('youth_converted_to_adult', False),  # Internal flag
                    '_tag_options': tag_options,
                })

                if norm_ref in self.bookings_require_unit_check:
                    unit_error = "Please check booking unit types before insertion"
                    if result['Error']:
                        result['Error'] += f" | {unit_error}"
                    else:
                        result['Error'] = unit_error
                    result['_highlight_yellow'] = True
                
                # Add Monday-specific columns ONLY if Monday file is provided
                # This keeps the output clean for Ventrata-only scenarios
                if is_colosseum_booking and should_include_monday_columns(self.scenario):
                    if 'monday_row' in booking_data:
                        monday_row = booking_data['monday_row']
                        
                        # Extract PNR
                        # Try both 'ticket pnr' and 'Ticket PNR' for case-insensitive matching
                        pnr_col = self.monday_col_map.get('ticket pnr') or self.monday_col_map.get('Ticket PNR')
                        if not pnr_col:
                            # Fallback: search for column containing 'pnr' (case-insensitive)
                            for col_name in monday_row.index:
                                if 'pnr' in str(col_name).lower():
                                    pnr_col = col_name
                                    break
                        
                        pnr_value = ''
                        if pnr_col and pnr_col in monday_row:
                            pnr_value = monday_row[pnr_col] if not pd.isna(monday_row[pnr_col]) else ''
                        result['PNR'] = pnr_value
                        
                        # Extract Ticket Group
                        ticket_group_col = self.monday_col_map.get('ticket group')
                        ticket_group_value = ''
                        if ticket_group_col and ticket_group_col in monday_row:
                            ticket_group_value = monday_row[ticket_group_col] if not pd.isna(monday_row[ticket_group_col]) else ''
                        result['Ticket Group'] = ticket_group_value
                        
                        # Generate TIX NOM from PNR
                        if pnr_value:
                            result['TIX NOM'] = generate_tix_nom(pnr_value)
                        else:
                            result['TIX NOM'] = ''
                        
                        logger.debug(f"Added Monday columns for {order_ref}: PNR={pnr_value[:20] if pnr_value else 'empty'}, TIX NOM={result.get('TIX NOM', '')}")
                    else:
                        # Monday file provided but no monday_row in booking_data
                        logger.warning(f"Monday file provided but no monday_row found for order {order_ref}")
                        result['PNR'] = ''
                        result['Ticket Group'] = ''
                        result['TIX NOM'] = ''
                
                results.append(result)
        else:
            # No travelers extracted - still create a row with error
            logger.warning(f"No travelers extracted for {order_ref}, creating empty result with error")
            
            travel_date_raw = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)
            travel_date = self._format_travel_date_for_output(travel_date_raw)
            
            # Special handling for Gold Hour / Twilight product
            if product_code == 'ROMARNEVEENG':
                language = 'Gold Hour / Twilight'
            
            # Aggregate all errors
            traveler_errors = list(pre_computed_errors)  # Copy pre-computed errors
            traveler_errors.append("No names could be extracted from booking")
            
            result = {
                'Travel Date': travel_date,
                'Order Reference': order_ref,
                'Full Name': '',
                'Unit Type': '',
                'Total Units': total_units,
                'Tour Time': tour_time,
                'Language': language,
                'Tour Type': tour_type,
                'Private Notes': private_notes,
            }

            if is_colosseum_booking:
                result.update({
                    'Change By': '',
                    'PNR': '',
                    'Ticket Group': '',
                    'Codice': '',
                    'Sigilo': '',
                })

            result.update({
                'Product Code': product_code,
                'Tag': '',
                'ID': '',
                'Reseller': reseller,
                'Error': ' | '.join(traveler_errors) if traveler_errors else '',
                '_youth_converted': False,
                '_tag_options': tag_options,
            })

            if norm_ref in self.bookings_require_unit_check:
                unit_error = "Please check booking unit types before insertion"
                if result['Error']:
                    result['Error'] += f" | {unit_error}"
                else:
                    result['Error'] = unit_error
                result['_highlight_yellow'] = True
            
            # Add Monday-specific columns if applicable
            if is_colosseum_booking and should_include_monday_columns(self.scenario):
                if 'monday_row' in booking_data:
                    monday_row = booking_data['monday_row']
                    
                    # Extract PNR
                    pnr_col = self.monday_col_map.get('ticket pnr') or self.monday_col_map.get('Ticket PNR')
                    if not pnr_col:
                        for col_name in monday_row.index:
                            if 'pnr' in str(col_name).lower():
                                pnr_col = col_name
                                break
                    
                    pnr_value = ''
                    if pnr_col and pnr_col in monday_row:
                        pnr_value = monday_row[pnr_col] if not pd.isna(monday_row[pnr_col]) else ''
                    result['PNR'] = pnr_value
                    
                    # Extract Ticket Group
                    ticket_group_col = self.monday_col_map.get('ticket group')
                    ticket_group_value = ''
                    if ticket_group_col and ticket_group_col in monday_row:
                        ticket_group_value = monday_row[ticket_group_col] if not pd.isna(monday_row[ticket_group_col]) else ''
                    result['Ticket Group'] = ticket_group_value
                    
                    # Generate TIX NOM from PNR
                    if pnr_value:
                        result['TIX NOM'] = generate_tix_nom(pnr_value)
                    else:
                        result['TIX NOM'] = ''
                else:
                    result['PNR'] = ''
                    result['Ticket Group'] = ''
                    result['TIX NOM'] = ''
            
            results.append(result)
        
        # Check for duplicate names within this booking; if found, try resolving via private notes
        has_dupes, duplicate_names = check_duplicates_in_booking(travelers)
        if has_dupes:
            logger.info(f"[DupCheck] {order_ref} has duplicates: {duplicate_names}, {travelers}")
        if has_dupes:
            unit_col = self.ventrata_col_map.get('unit')
            parser_travelers, _ = build_travelers_from_private_notes(private_notes, ventrata_rows, unit_col, travel_date_raw)

            resolved_duplicates = False

            if parser_travelers:
                logger.info(f"[DupCheck] Parser returned {len(parser_travelers)} travelers for {order_ref}")
                booking_units = []
                if unit_col and unit_col in ventrata_rows.columns:
                    for _, row in ventrata_rows.iterrows():
                        unit_val = row.get(unit_col)
                        if pd.notna(unit_val) and str(unit_val).strip():
                            booking_units.append(str(unit_val).strip())
                logger.info(f"[DupCheck] Booking units for {order_ref}: {booking_units}")

                def _normalize_unit(value):
                    if value is None:
                        return ''
                    return str(value).strip().lower()

                parser_units = [_normalize_unit(p.get('unit_type')) for p in parser_travelers]
                booking_units_norm = [_normalize_unit(u) for u in booking_units]
                logger.info(f"[DupCheck] Parser units for {order_ref}: {parser_units}")

                parser_unit_counts = Counter(parser_units)
                booking_unit_counts = Counter(booking_units_norm)

                if booking_units_norm and parser_unit_counts == booking_unit_counts:
                    reordered_travelers = []
                    buckets = {}
                    for traveler, unit in zip(parser_travelers, parser_units):
                        buckets.setdefault(unit, []).append(traveler)

                    reorder_failed = False
                    for unit in booking_units_norm:
                        bucket = buckets.get(unit)
                        if bucket:
                            reordered_travelers.append(bucket.pop(0))
                        else:
                            reorder_failed = True
                            logger.warning(f"[DupCheck] Could not reorder parser travelers for unit {unit} in {order_ref}")
                            break

                    if reorder_failed:
                        logger.info(f"[DupCheck] Parser traveler reordering failed for {order_ref}")
                        reordered_travelers = []

                else:
                    reordered_travelers = []
                    if booking_units_norm:
                        logger.info(f"[DupCheck] Unit counts mismatch for {order_ref}: parser={parser_unit_counts}, booking={booking_unit_counts}")
                    else:
                        logger.info(f"[DupCheck] No booking units found for {order_ref}")

                if reordered_travelers:
                    parser_travelers = reordered_travelers
                    logger.info(f"[DupCheck] Units match for {order_ref}; swapping to parser travelers")
                    if extractor_type in ['gyg_standard', 'gyg_mda']:
                        parser_travelers = self._map_travelers_to_ids(parser_travelers, ventrata_rows, order_ref)
                        logger.info(f"[DupCheck] Parser travelers mapped to IDs for {order_ref}")

                    unit_col = self.ventrata_col_map.get('unit')
                    unit_counts = get_unit_counts(ventrata_rows, unit_col) if unit_col else {}

                    has_unit_types = all(t.get('unit_type') is not None for t in parser_travelers)
                    if extractor_type != 'non_gyg' and not has_unit_types:
                        parser_travelers = self._assign_unit_types(
                            parser_travelers,
                            unit_counts,
                            product_tags_str,
                            customer_country,
                            extractor_type in ['gyg_standard', 'gyg_mda']
                        )

                    if product_tags_str:
                        for traveler in parser_travelers:
                            unit_type = traveler.get('unit_type')
                            if unit_type:
                                converted = convert_infant_to_child_for_colosseum(unit_type, product_tags_str)
                                traveler['unit_type'] = converted

                    travelers = parser_travelers

                    for idx, traveler in enumerate(travelers):
                        if idx >= len(results):
                            break
                        result = results[idx]
                        logger.info(f"[DupCheck] Updating row {idx} for {order_ref} -> {traveler['name']} ({traveler.get('unit_type')})")
                        result['Full Name'] = traveler['name']
                        result['Unit Type'] = traveler.get('unit_type', '')
                        if extractor_type in ['gyg_standard', 'gyg_mda']:
                            result['ID'] = traveler.get('ventrata_id', result.get('ID', ''))

                    resolved_duplicates = True
                    logger.info(f"Resolved duplicate names for {order_ref} using private notes parser")

            if not resolved_duplicates:
                dup_error = "Duplicated names in the booking"
                duplicate_names_set = set(duplicate_names)
                for result in results:
                    if result['Full Name'] in duplicate_names_set:
                        if result['Error']:
                            result['Error'] += f" | {dup_error}"
                        else:
                            result['Error'] = dup_error
        
        return results
    
    def _apply_post_processing(self, results_df):
        """
        Apply post-processing validations.
        
        Note: Results are kept in original Ventrata file order.
        No sorting is applied to preserve the order bookings appear in the source file.
        
        Args:
            results_df: Results DataFrame
            
        Returns:
            pd.DataFrame: Post-processed DataFrame
        """
        # Remove internal columns that shouldn't appear in output
        if '_highlight_yellow' in results_df.columns:
            results_df = results_df.drop(columns=['_highlight_yellow'])
        
        # No sorting - preserve original Ventrata file order
        # Bookings are processed in the order they appear in the Ventrata file
        # via _get_ventrata_ordered_data() or _get_monday_ordered_data()
        
        return results_df

