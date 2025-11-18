"""
Youth and age validation.

Handles:
- EU country detection
- Youth booking validation (18-25 age range)
- Age vs unit type mismatch detection
"""

import pandas as pd
import logging

from config import EU_COUNTRIES, AGE_YOUTH_MIN, AGE_YOUTH_MAX

logger = logging.getLogger(__name__)


def is_eu_country(country):
    """
    Check if a country is in the European Union.
    
    Args:
        country: Country name or code
        
    Returns:
        bool: True if country is in EU, False otherwise
        
    Example:
        "FRANCE" -> True
        "FR" -> True
        "USA" -> False
    """
    if not country or pd.isna(country):
        return False
    
    country_upper = str(country).strip().upper()
    return country_upper in EU_COUNTRIES


def validate_youth_booking(travelers, unit_counts, customer_country, is_gyg=False):
    """
    Validate youth bookings (only for EU countries).
    
    Youth validation rules:
    - Youth = 18-25 years old
    - Only validate for EU countries
    - For non-EU countries, convert Youth to Adult (no error)
    - For EU countries, verify ages match youth category
    
    Args:
        travelers: List of traveler dicts with age info
        unit_counts: Dict with unit type counts {'Adult': 2, 'Child': 1, 'Youth': 1}
        customer_country: Customer country string
        is_gyg: Whether this is a GYG booking (more strict validation)
        
    Returns:
        list: List of error messages
    """
    errors = []
    
    youth_unit_count = unit_counts.get('Youth', 0)
    
    if youth_unit_count == 0:
        return errors
    
    # Check if EU country
    is_eu = is_eu_country(customer_country)
    
    if not is_eu:
        # Non-EU countries: No validation, just note the conversion
        logger.info(f"Non-EU country {customer_country} with {youth_unit_count} youth units - will convert to Adult")
        return errors
    
    # EU country validation
    logger.info(f"Validating {youth_unit_count} youth units for EU country {customer_country}")
    
    # Count travelers by age category
    youth_travelers = sum(1 for t in travelers if t.get('is_youth_by_age', False))
    
    # For GYG bookings, do comprehensive validation
    if is_gyg:
        child_travelers = sum(1 for t in travelers if t.get('is_child_by_age', False))
        adult_travelers = sum(1 for t in travelers if t.get('is_adult_by_age', False))
        
        child_unit_count = sum(unit_counts.get(unit, 0) for unit in ['Child', 'Infant'])
        adult_unit_count = unit_counts.get('Adult', 0)
        
        # Check unit count mismatches
        if youth_travelers != youth_unit_count:
            errors.append(f"Youth unit mismatch: {youth_unit_count} youth units booked but {youth_travelers} travelers in youth age range (18-25)")
        
        if child_travelers != child_unit_count:
            errors.append(f"Child unit mismatch: {child_unit_count} child units booked but {child_travelers} travelers under 18")
        
        if adult_travelers != adult_unit_count:
            errors.append(f"Adult unit mismatch: {adult_unit_count} adult units booked but {adult_travelers} travelers over 25")
    else:
        # Non-GYG EU booking: Simple flag
        if youth_unit_count > 0:
            errors.append("Youth in the booking")
    
    return errors


def validate_age_unit_type_match(travelers, assigned_unit_types):
    """
    Validate that assigned unit types match actual ages.
    
    Args:
        travelers: List of traveler dicts with age info
        assigned_unit_types: List of assigned unit types (same length as travelers)
        
    Returns:
        list: List of mismatch error messages
    """
    errors = []
    
    for traveler, unit_type in zip(travelers, assigned_unit_types):
        name = traveler.get('name', 'Unknown')
        age = traveler.get('age')
        
        if age is None:
            continue
        
        is_child_by_age = traveler.get('is_child_by_age', False)
        is_youth_by_age = traveler.get('is_youth_by_age', False)
        is_adult_by_age = traveler.get('is_adult_by_age', False)
        
        # Check for mismatches
        if is_child_by_age and unit_type == 'Adult':
            errors.append(f"Child {name} (age {age:.1f}) booked as Adult")
        elif is_adult_by_age and unit_type == 'Child':
            errors.append(f"Adult {name} (age {age:.1f}) booked as Child ")
        elif not is_youth_by_age and unit_type == 'Youth':
            errors.append(f"Youth unit {name} (age {age:.1f}) is outside 18-25 range")
    
    return errors

