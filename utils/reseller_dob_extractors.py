"""
Reseller-specific DOB extraction utilities.

Handles different DOB formats from different reseller platforms.
Each reseller can have its own extraction function registered here.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _extract_viator_dobs(public_notes: str) -> List[str]:
    """
    Extract DOBs from Viator Q&A format:
    Q:Date of Birth
    A:09/05/1965, 28/11/2006, 17/11/1966
    
    Args:
        public_notes: Public notes text
        
    Returns:
        List of DOB strings in DD/MM/YYYY format
    """
    if not public_notes:
        return []
    
    # Pattern to match "Q:Date of Birth" followed by "A:" with comma-separated dates
    pattern = r'Q:\s*Date of Birth\s*\n\s*A:\s*([^\n]+)'
    match = re.search(pattern, public_notes, re.IGNORECASE | re.MULTILINE)
    
    if not match:
        # Try alternative pattern without newline
        pattern = r'Q:\s*Date of Birth[^\n]*A:\s*([^\n]+)'
        match = re.search(pattern, public_notes, re.IGNORECASE)
    
    if not match:
        return []
    
    # Extract comma-separated dates
    dates_str = match.group(1).strip()
    # Split by comma and clean each date
    dates = [d.strip() for d in dates_str.split(',') if d.strip()]
    
    # Validate date format (DD/MM/YYYY)
    valid_dates = []
    for date_str in dates:
        # Check if it matches DD/MM/YYYY format
        if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
            valid_dates.append(date_str)
        else:
            logger.debug(f"Viator: Skipping invalid date format: {date_str}")
    
    if valid_dates:
        logger.info(f"Viator: Extracted {len(valid_dates)} DOBs: {valid_dates}")
    
    return valid_dates


def _extract_gyg_standard_dobs(public_notes: str) -> List[str]:
    """
    Extract DOBs from GYG Standard format public notes.
    
    Supports two formats:
    - DD/MM/YYYY format: "Date of Birth: 15/03/1990"
    - YYYY-MM-DD format: "Date of Birth: 1990-03-15"
    
    Args:
        public_notes: Public notes text
        
    Returns:
        List of DOB strings in order of appearance
    """
    if not public_notes:
        return []
    
    # Fast string check before regex - skip if "Date of Birth:" doesn't exist
    public_notes_lower = public_notes.lower()
    if 'date of birth:' not in public_notes_lower:
        return []  # Early exit - pattern can't match
    
    # Pattern 1: DD/MM/YYYY format
    dob_pattern_slash = r"Date of Birth:\s*(\d{2}/\d{2}/\d{4})"
    slash_dobs = re.findall(dob_pattern_slash, public_notes, re.IGNORECASE)
    
    # Pattern 2: YYYY-MM-DD format
    dob_pattern_dash = r"Date of Birth:\s*(\d{4}-\d{2}-\d{2})"
    dash_dobs = re.findall(dob_pattern_dash, public_notes, re.IGNORECASE)
    
    # Combine maintaining order of appearance
    all_dobs = slash_dobs + dash_dobs
    
    if all_dobs:
        logger.info(f"GYG Standard: Extracted {len(all_dobs)} DOBs")
    
    return all_dobs


def match_viator_dobs_to_travelers(travelers: List[Dict[str, Any]], extracted_dobs: List[str], 
                                    travel_date: Any, customer_country: str) -> List[Dict[str, Any]]:
    """
    Match Viator DOBs to travelers based on unit type and age category.
    
    Strategy:
    1. Sort DOBs from youngest to oldest
    2. Calculate ages for all DOBs
    3. Assign DOBs to travelers by unit type:
       - Child unit → youngest DOB that is < 18
       - Youth unit → DOB that is 18-24 (EU) or >=18 (non-EU)
       - Adult unit → oldest DOB that is >= 25 (EU) or >=18 (non-EU)
    4. After assignment, validate and convert unit types if needed
    
    Args:
        travelers: List of traveler dicts with unit_type
        extracted_dobs: List of DOB strings
        travel_date: Travel date for age calculation
        customer_country: Customer country for EU/non-EU determination
        
    Returns:
        List of travelers with matched DOBs
    """
    from utils.age_calculator import calculate_age_on_travel_date
    from validators import is_eu_country
    from config import AGE_CHILD_MAX, AGE_YOUTH_MIN, AGE_YOUTH_MAX, AGE_ADULT_MIN
    
    if not extracted_dobs or not travel_date:
        return travelers
    
    is_eu = is_eu_country(customer_country)
    
    # Step 1: Calculate ages for all DOBs and sort from youngest to oldest
    dob_info_list = []
    for dob_str in extracted_dobs:
        age = calculate_age_on_travel_date(dob_str, travel_date)
        if age is not None:
            dob_info_list.append({
                'dob': dob_str,
                'age': age,
                'assigned': False
            })
    
    # Sort by age (youngest first)
    dob_info_list.sort(key=lambda x: x['age'])
    
    # Step 2: Group travelers by unit type
    # Map Infant to Child for DOB matching (both need DOBs < 18)
    child_travelers = [t for t in travelers if t.get('unit_type', '').strip().lower() in ['child', 'infant']]
    youth_travelers = [t for t in travelers if t.get('unit_type', '').strip().lower() == 'youth']
    adult_travelers = [t for t in travelers if t.get('unit_type', '').strip().lower() == 'adult']
    
    # Step 3: Assign DOBs to Child travelers (youngest DOBs that are < 18)
    for traveler in child_travelers:
        for dob_info in dob_info_list:
            if not dob_info['assigned'] and dob_info['age'] < AGE_CHILD_MAX:
                traveler['dob'] = dob_info['dob']
                traveler['age'] = dob_info['age']
                # Age flags will be set in processor based on country
                dob_info['assigned'] = True
                unit_type = traveler.get('unit_type', 'Unknown')
                logger.debug(f"Viator: Assigned DOB {dob_info['dob']} (age {dob_info['age']:.1f}) to {unit_type} {traveler.get('name', 'Unknown')}")
                break
    
    # Step 4: Assign DOBs to Youth travelers (DOBs that are 18-24 for EU, >=18 for non-EU)
    for traveler in youth_travelers:
        for dob_info in dob_info_list:
            if not dob_info['assigned']:
                if is_eu:
                    # EU: Youth is 18-24
                    if AGE_YOUTH_MIN <= dob_info['age'] < AGE_YOUTH_MAX:
                        traveler['dob'] = dob_info['dob']
                        traveler['age'] = dob_info['age']
                        # Age flags will be set in processor based on country
                        dob_info['assigned'] = True
                        logger.debug(f"Viator: Assigned DOB {dob_info['dob']} (age {dob_info['age']:.1f}) to Youth {traveler.get('name', 'Unknown')}")
                        break
                else:
                    # Non-EU: Youth is >=18 (will convert to Adult later)
                    if dob_info['age'] >= AGE_CHILD_MAX:
                        traveler['dob'] = dob_info['dob']
                        traveler['age'] = dob_info['age']
                        # Age flags will be set in processor based on country
                        dob_info['assigned'] = True
                        logger.debug(f"Viator: Assigned DOB {dob_info['dob']} (age {dob_info['age']:.1f}) to Youth {traveler.get('name', 'Unknown')}")
                        break
    
    # Step 5: Assign DOBs to Adult travelers (oldest DOBs that are >=25 for EU, >=18 for non-EU)
    # Sort adult DOBs from oldest to youngest for assignment
    adult_dobs = [d for d in dob_info_list if not d['assigned']]
    adult_dobs.sort(key=lambda x: x['age'], reverse=True)  # Oldest first
    
    for traveler in adult_travelers:
        for dob_info in adult_dobs:
            if not dob_info['assigned']:
                if is_eu:
                    # EU: Adult is >= 25
                    if dob_info['age'] >= AGE_ADULT_MIN:
                        traveler['dob'] = dob_info['dob']
                        traveler['age'] = dob_info['age']
                        # Age flags will be set in processor based on country
                        dob_info['assigned'] = True
                        logger.debug(f"Viator: Assigned DOB {dob_info['dob']} (age {dob_info['age']:.1f}) to Adult {traveler.get('name', 'Unknown')}")
                        break
                else:
                    # Non-EU: Adult is >= 18
                    if dob_info['age'] >= AGE_CHILD_MAX:
                        traveler['dob'] = dob_info['dob']
                        traveler['age'] = dob_info['age']
                        # Age flags will be set in processor based on country
                        dob_info['assigned'] = True
                        logger.debug(f"Viator: Assigned DOB {dob_info['dob']} (age {dob_info['age']:.1f}) to Adult {traveler.get('name', 'Unknown')}")
                        break
    
    # Step 6: Store original unit types for validation
    # Unit type correction will be handled centrally by _smart_match_unit_types in processor.py
    for traveler in travelers:
        unit_type = traveler.get('unit_type', '').strip()
        if 'original_unit_type' not in traveler:
            traveler['original_unit_type'] = unit_type
        if '_original_unit_type_for_validation' not in traveler:
            traveler['_original_unit_type_for_validation'] = unit_type
    
    # Log any unmatched DOBs
    unmatched_dobs = [d for d in dob_info_list if not d['assigned']]
    if unmatched_dobs:
        logger.warning(f"Viator: {len(unmatched_dobs)} DOBs could not be matched: {[d['dob'] for d in unmatched_dobs]}")
    
    # Log any travelers without DOBs
    unmatched_travelers = [t for t in travelers if not t.get('dob')]
    if unmatched_travelers:
        logger.warning(f"Viator: {len(unmatched_travelers)} travelers could not be matched with DOBs: {[t.get('name', 'Unknown') for t in unmatched_travelers]}")
    
    return travelers


# Registry of reseller-specific DOB extractors
# Key: reseller name (lowercase, partial match)
# Value: function that takes public_notes and returns List[str] of DOBs
RESELLER_DOB_EXTRACTORS = {
    'viator': _extract_viator_dobs,
    'getyourguide': _extract_gyg_standard_dobs,
    # Add more resellers here as needed:
    # 'tripadvisor': _extract_tripadvisor_dobs,
    # 'expedia': _extract_expedia_dobs,
}


def extract_dobs_by_reseller(public_notes: str, reseller: str) -> List[str]:
    """
    Extract DOBs from public notes based on reseller type.
    
    Args:
        public_notes: Public notes text
        reseller: Reseller name string
        
    Returns:
        List of DOB strings (empty list if no DOBs found or reseller not supported)
    """
    if not public_notes or not reseller:
        return []
    
    reseller_lower = str(reseller).lower()
    
    # Check if we have a specific extractor for this reseller
    for reseller_key, extractor_func in RESELLER_DOB_EXTRACTORS.items():
        if reseller_key in reseller_lower:
            try:
                dobs = extractor_func(public_notes)
                if dobs:
                    logger.info(f"Extracted {len(dobs)} DOBs using {reseller_key} format for reseller {reseller}")
                return dobs
            except Exception as e:
                logger.warning(f"Error extracting DOBs for {reseller_key}: {e}")
                return []
    
    return []

