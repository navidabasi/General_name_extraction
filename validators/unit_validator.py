"""
Unit count validation.

Validates:
- Unit count vs traveler count mismatches
- Missing DOBs for bookings withmixed unit types
- Age consistency for mixed bookings
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def check_unit_traveler_mismatch(total_units, total_travelers, platform=""):
    """
    Check if number of units matches number of travelers.
    
    Args:
        total_units: Total unit count from booking
        total_travelers: Number of travelers extracted
        platform: Platform name for error message
        
    Returns:
        str: Error message if mismatch, empty string otherwise
    """
    if total_units != total_travelers:
        platform_msg = f" {platform}" if platform else ""
        error = f"Number of provided units ({total_units}) and Travelers ({total_travelers}) in the{platform_msg} booking does not match"
        logger.warning(error)
        return error
    
    return ""


def check_missing_dobs(has_mixed_units, dobs, names, platform="GYG"):
    """
    Check if DOBs are missing for bookings with mixed unit types.
    
    Args:
        has_mixed_units: Whether booking has both child and adult units
        dobs: List of DOB strings
        names: List of names
        platform: Platform name for error message
        
    Returns:
        str: Error message if DOBs missing, empty string otherwise
    """
    if has_mixed_units and (not dobs or len(dobs) < len(names)):
        error = f"{platform} booking no Date of Birth indicated"
        logger.warning(error)
        return error
    
    return ""


def check_all_under_18(dobs, travel_date, has_mixed_units):
    """
    Check if all travelers are under 18 with mixed unit types.
     
    Args:
        dobs: List of DOB strings
        travel_date: Travel date for age calculation (uses actual travel date, not current date)
        has_mixed_units: Whether booking has mixed unit types
        
    Returns:
        str: Error message if all under 18, empty string otherwise
    """
    if not has_mixed_units or not dobs:
        return ""
    
    if not travel_date:
        logger.warning("No travel date provided for age validation")
        return ""
    
    from utils.age_calculator import calculate_age_on_travel_date
    
    all_under_18 = True
    
    for dob_str in dobs:
        # Use the standardized age calculation function
        age_years = calculate_age_on_travel_date(dob_str, travel_date)
        
        if age_years is None:
            # If age calculation fails, assume not all under 18 (don't flag error)
            logger.warning(f"Could not calculate age for DOB {dob_str}")
            all_under_18 = False
            break
        
        if age_years >= 18:
            all_under_18 = False
            break
    
    if all_under_18:
        error = "All travelers under 18 with mixed unit types"
        logger.warning(error)
        return error
    
    return ""


def check_only_child_infant(unit_counts):
    """
    Check if booking has only Child/Infant units (no adult supervision).
    
    Args:
        unit_counts: Dict with unit type counts
        
    Returns:
        str: Error message if only children, empty string otherwise
    """
    child_count = sum(unit_counts.get(unit, 0) for unit in ['Child', 'Infant'])
    adult_count = sum(unit_counts.get(unit, 0) for unit in ['Adult', 'Youth'])
    
    if child_count > 0 and adult_count == 0:
        error = "Booking has only Child/Infant units"
        logger.warning(error)
        return error
    
    return ""


def get_unit_counts(booking_rows, unit_column='Unit'):
    """
    Get unit type counts from booking rows.
    
    Args:
        booking_rows: DataFrame rows for a booking
        unit_column: Name of the unit column
        
    Returns:
        dict: Unit type counts
    """
    if booking_rows.empty:
        return {}
    
    # Handle case-insensitive column lookup
    actual_col = None
    for col in booking_rows.columns:
        if col.lower() == unit_column.lower():
            actual_col = col
            break
    
    if actual_col is None:
        logger.warning(f"Unit column '{unit_column}' not found")
        return {}
    
    return booking_rows[actual_col].value_counts().to_dict()

