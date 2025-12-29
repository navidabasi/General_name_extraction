"""
Reseller-specific DOB extraction utilities.

Handles different DOB formats from different reseller platforms.
Each reseller can have its own extraction function registered here.
"""

import re
import logging
from typing import List

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

