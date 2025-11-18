"""
Duplicate name detection within bookings.

Checks for duplicate names within the same booking,
ignoring unit type indicators like "(Adult)" or "(Child)".
"""

import re
import logging

logger = logging.getLogger(__name__)


def check_duplicates_in_booking(travelers_list):
    """
    Check for duplicate names within a booking.
    
    Removes unit type indicators (e.g., "(Adult)", "(Child)") 
    before comparing names to detect true duplicates.
    
    Args:
        travelers_list: List of traveler dicts with 'name' key
        
    Returns:
        tuple: (has_duplicates: bool, duplicate_names: list)
        
    Example:
        travelers = [
            {'name': 'John Smith (Adult)'},
            {'name': 'John Smith (Child)'},
            {'name': 'Jane Doe'}
        ]
        -> (True, ['John Smith (Adult)', 'John Smith (Child)'])
    """
    if not travelers_list:
        return False, []
    
    # Extract base names (without unit type indicators)
    names_in_booking = []
    for traveler in travelers_list:
        full_name = str(traveler.get('name', '')).strip()
        if full_name:
            # Remove unit type indicators like "(Adult)", "(Child)"
            base_name = re.sub(r'\s*\([^)]*\)\s*$', '', full_name).strip()
            names_in_booking.append((base_name, full_name))
    
    # Check for duplicates based on base names
    base_names = [name[0] for name in names_in_booking]
    unique_base_names = set(base_names) #only keeps unique values and removes duplicates.
    
    if len(base_names) != len(unique_base_names): #if the length of the base names is not equal to the length of the unique base names, then there are duplicates
        duplicate_names = []
        for base_name in unique_base_names:
            count = base_names.count(base_name)
            if count > 1:
                # Find all full names that have this base name
                matching_full_names = [full for base, full in names_in_booking if base == base_name]
                duplicate_names.extend(matching_full_names)
        
        logger.info(f"Found duplicate names in booking: {duplicate_names}")
        return True, list(set(duplicate_names))
    
    return False, []


def get_duplicate_error_message(duplicate_names):
    """
    Generate error message for duplicate names.
    
    Args:
        duplicate_names: List of duplicate name strings
        
    Returns:
        str: Error message
    """
    return f"Duplicated names in the booking: {', '.join(set(duplicate_names))}"
