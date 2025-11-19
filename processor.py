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

from config import GYG_MDA_PLATFORM, GYG_STANDARD_PLATFORMS, ALL_GYG_PLATFORMS
from utils.normalization import (
    normalize_ref, normalize_time,
    extract_language_from_product_code,
    extract_tour_type_from_product_code,
    standardize_column_names,
    get_column_value
)
from utils.age_calculator import categorize_age, convert_infant_to_child_for_colosseum
from utils.tix_nom_generator import generate_tix_nom
from utils.scenario_handler import determine_scenario, should_include_monday_columns, ProcessingScenario
from extractors import GYGStandardExtractor, GYGMDAExtractor, NonGYGExtractor
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
    
    def __init__(self, ventrata_df, monday_df=None):
        """
        Initialize processor with data.
        
        Args:
            ventrata_df: Ventrata DataFrame (required)
            monday_df: Monday DataFrame (optional)
        """
        self.ventrata_df = ventrata_df
        self.monday_df = monday_df
        
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
        
        # Pre-computed error caches
        self.booking_errors_cache = {}
        
        # Determine processing scenario
        self.scenario = determine_scenario(ventrata_df, monday_df)
        logger.info(f"Processing scenario: {self.scenario.value}")
    
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
                'Order Reference': order_ref,
                'Unit Type': '',
                'Total Units': 0,
                'Error': 'No Ventrata data found for this booking'
            }]
        
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
        
        # Build booking data dict for all extractors (includes travel_date for age calculation)
        # Get monday_row from the passed booking_data parameter
        monday_row = booking_data.get('monday_row') if isinstance(booking_data, dict) else None
        
        # Build booking data dict with both Ventrata and Monday data
        booking_data = self._build_booking_data_dict(first_row, monday_row)
        
        # Preserve monday_row in booking_data for later use
        if monday_row is not None:
            booking_data['monday_row'] = monday_row
        
        # For non-GYG, pass booking data for structured column access
        if extractor_type == 'non_gyg':
            # Need to process each row separately for non-GYG
            travelers = []
            for _, row in ventrata_rows.iterrows():
                # Build booking data with Monday row if available
                row_booking_data = self._build_booking_data_dict(row, monday_row)
                row_travelers = self.extractors['non_gyg'].extract_travelers(public_notes, order_ref, row_booking_data)
                travelers.extend(row_travelers)
            
            # If non-GYG extraction failed (empty structured fields), no fallback available
            if not travelers:
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
                    # Both GYG Standard and MDA failed
                    logger.warning(f"All extraction methods failed for GYG order {order_ref}")
                else:
                    logger.info(f"GYG MDA fallback successful for {order_ref}: extracted {len(travelers)} travelers")
            else:
                logger.debug(f"GYG Standard extraction successful for {order_ref}: extracted {len(travelers)} travelers")
        
        else:
            # Fallback for any other extractor type
            extractor = self.extractors.get(extractor_type)
            if extractor:
                travelers = extractor.extract_travelers(public_notes, order_ref, booking_data)
            else:
                travelers = []
        
        # Get pre-computed errors
        pre_computed_errors = self.booking_errors_cache.get(norm_ref, [])
        
        # Get booking-level info
        total_units = len(ventrata_rows)
        
        # Extract travel_date from Ventrata only (handles both merged and non-merged scenarios)
        travel_date = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)
        
        # Get tour info
        product_code_col = self.ventrata_col_map.get('product code')
        product_code = first_row[product_code_col] if product_code_col else ''
        
        tour_time_col = self.ventrata_col_map.get('tour time')
        tour_time = normalize_time(first_row[tour_time_col]) if tour_time_col else ''
        
        language = extract_language_from_product_code(product_code)
        tour_type = extract_tour_type_from_product_code(product_code)
        
        private_notes_col = self.ventrata_col_map.get('private notes')
        private_notes = str(first_row[private_notes_col]) if private_notes_col else ''
        
        product_tags_col = self.ventrata_col_map.get('product tags')
        product_tags = str(first_row[product_tags_col]) if product_tags_col else ''
        
        # Get customer country and platform info for youth handling
        customer_country_col = self.ventrata_col_map.get('customer country')
        customer_country = first_row[customer_country_col] if customer_country_col else ''
        is_gyg = extractor_type in ['gyg_standard', 'gyg_mda']
        
        # Assign unit types if we have travelers
        if travelers:
            unit_col = self.ventrata_col_map.get('unit')
            unit_counts = get_unit_counts(ventrata_rows, unit_col) if unit_col else {}
            
            # Check if unit types are already assigned (e.g., by Spacy fallback)
            has_unit_types = all(t.get('unit_type') is not None for t in travelers)
            
            if not has_unit_types:
                # Assign unit types based on ages, unit counts, country, and platform
                travelers = self._assign_unit_types(
                    travelers, 
                    unit_counts, 
                    product_tags, 
                    customer_country, 
                    is_gyg
                )
            else:
                logger.debug(f"Unit types already assigned for {order_ref}, skipping assignment")
        
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
                
                # Build result dict
                result = {
                    'Full Name': traveler['name'],
                    'Order Reference': order_ref,
                    'Travel Date': travel_date,
                    'Unit Type': traveler.get('unit_type', ''),
                    'Total Units': total_units,
                    'Tour Time': tour_time,
                    'Language': language,
                    'Tour Type': tour_type,
                    'Private Notes': private_notes,
                    'Reseller': reseller,
                    'Error': ' | '.join(traveler_errors) if traveler_errors else '',
                    '_youth_converted': traveler.get('youth_converted_to_adult', False)  # Internal flag for coloring
                }
                
                # Add Monday-specific columns ONLY if Monday file is provided
                # This keeps the output clean for Ventrata-only scenarios
                if should_include_monday_columns(self.scenario):
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
                        
                        logger.debug(f"Added Monday columns for {order_ref}: PNR={pnr_value[:20] if pnr_value else 'empty'}, TIX NOM={result['TIX NOM']}")
                    else:
                        # Monday file provided but no monday_row in booking_data
                        logger.warning(f"Monday file provided but no monday_row found for order {order_ref}")
                        result['PNR'] = ''
                        result['Ticket Group'] = ''
                        result['TIX NOM'] = ''
                # If no Monday file, these columns are not added at all (keeps output clean)
                
                results.append(result)
        else:
            # No travelers extracted - still create a row with error
            logger.warning(f"No travelers extracted for {order_ref}, creating empty result with error")
            
            travel_date_raw = self._extract_travel_date(first_row, monday_row=None, order_ref=order_ref)
            travel_date = self._format_travel_date_for_output(travel_date_raw)
            
            # Aggregate all errors
            traveler_errors = list(pre_computed_errors)  # Copy pre-computed errors
            traveler_errors.append("No names could be extracted from booking")
            
            result = {
                'Full Name': '',
                'Order Reference': order_ref,
                'Travel Date': travel_date,
                'Unit Type': '',
                'Total Units': total_units,
                'Tour Time': tour_time,
                'Language': language,
                'Tour Type': tour_type,
                'Private Notes': private_notes,
                'Reseller': reseller,
                'Error': ' | '.join(traveler_errors) if traveler_errors else '',
                '_youth_converted': False
            }
            
            # Add Monday-specific columns if applicable
            if should_include_monday_columns(self.scenario):
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
        
        # Check for duplicate names within this booking
        has_dupes, duplicate_names = check_duplicates_in_booking(travelers)
        if has_dupes:
            dup_error = f"Duplicated names in the booking"
            # Only flag error for travelers whose names are actually duplicated
            duplicate_names_set = set(duplicate_names)
            for result in results:
                # Check if this specific name is in the duplicates list
                if result['Full Name'] in duplicate_names_set:
                    if result['Error']:
                        result['Error'] += f" | {dup_error}"
                    else:
                        result['Error'] = dup_error
        
        return results
    
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
        }
    
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
        child_units = sum(unit_counts.get(unit, 0) for unit in ['Child', 'Infant'])
        youth_units = unit_counts.get('Youth', 0)
        adult_units = unit_counts.get('Adult', 0)
        
        # Check if EU country
        is_eu = is_eu_country(customer_country)
        
        # Initialize all travelers as unassigned
        for traveler in sorted_travelers:
            traveler['unit_type'] = None
            traveler['youth_converted_to_adult'] = False  # Flag for coloring
        
        # Step 1: Assign Child/Infant units (only if Child units exist in booking)
        if child_units > 0:
            child_assigned = 0
            for traveler in sorted_travelers:
                age = traveler.get('age')
                # Only assign Child/Infant to travelers under 18
                if age is not None and age < 18 and child_assigned < child_units:
                    base_unit = 'Child'
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
                        traveler['unit_type'] = 'Youth'
                        youth_assigned += 1
                        logger.debug(f"Non-GYG: Keeping Youth unit for {traveler.get('name')}")
                
                # Rule 2: GYG EU bookings - Keep Youth as booked (preserve unit type)
                # Validation will flag errors if age is outside 18-24 range
                elif is_gyg and is_eu:
                    if youth_assigned < youth_units:
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
                        traveler['unit_type'] = 'Adult'
                    elif child_units > 0:
                        traveler['unit_type'] = 'Child'
                    elif youth_units > 0:
                        traveler['unit_type'] = 'Youth'
                    else:
                        # No units available at all - default to Adult
                        traveler['unit_type'] = 'Adult'
                else:
                    # Has age but wasn't assigned - unit count mismatch
                    logger.warning(f"Unit type not assigned for {name} (age {age:.1f}) - unit count mismatch")
                    # Assign based on age as fallback
                    if age < 18:
                        traveler['unit_type'] = 'Child'
                    elif 18 <= age < 25:
                        traveler['unit_type'] = 'Youth'
                    else:
                        traveler['unit_type'] = 'Adult'
        
        return sorted_travelers
    
    def _apply_post_processing(self, results_df):
        """
        Apply post-processing validations and sorting.
        
        Args:
            results_df: Results DataFrame
            
        Returns:
            pd.DataFrame: Post-processed DataFrame
        """
        # Sort by Order Reference to keep bookings together
        if not results_df.empty and 'Order Reference' in results_df.columns:
            results_df = results_df.sort_values('Order Reference')
        
        return results_df

