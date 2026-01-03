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


def validate_youth_booking(travelers, unit_counts, customer_country, is_gyg=False, is_colosseum_booking=False):
    """
    Validate youth bookings (only for EU countries).
    Also flags travelers as "Possible Youth" if age 18-25, Adult unit, EU country, and Colosseum booking.
    
    Youth validation rules:
    - Youth = 18-25 years old
    - Only validate for EU countries
    - For non-EU countries, convert Youth to Adult (no error)
    - For EU countries, verify ages match youth category
    - Flag "Possible Youth" for travelers age 18-25 with Adult units in EU countries (Colosseum bookings only)
    
    Args:
        travelers: List of traveler dicts with age info
        unit_counts: Dict with unit type counts {'Adult': 2, 'Child': 1, 'Youth': 1}
        customer_country: Customer country string
        is_gyg: Whether this is a GYG booking (more strict validation)
        is_colosseum_booking: Whether this is a Colosseum booking (required for Possible Youth flagging)
        
    Returns:
        list: List of error messages
    """
    errors = []
    
    # Check if EU country
    is_eu = is_eu_country(customer_country)
    
    # Check for Possible Youth (age 18-24, Adult unit, EU country, Colosseum booking only)
    if is_eu and is_colosseum_booking:
        for traveler in travelers:
            age = traveler.get('age')
            unit_type = traveler.get('unit_type', '').lower()
            if (age is not None and 
                AGE_YOUTH_MIN <= age < AGE_YOUTH_MAX and 
                unit_type == 'adult'):
                traveler['possible_youth'] = True
                logger.debug(f"Flagging {traveler.get('name')} as Possible Youth "
                            f"(age={age}, unit=Adult, EU country={customer_country}, Colosseum booking)")
    
    youth_unit_count = unit_counts.get('Youth', 0)
    
    if youth_unit_count == 0:
        return errors
    
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
    
    Note: For non-EU customers, youth age range (18-24) is not flagged as error
    when booked as Adult, since Youth doesn't exist for non-EU (18+ = Adult).
    Non-EU youth conversions are indicated by light yellow coloring instead.
    
    Args:
        travelers: List of traveler dicts with age flags (is_child_by_age, is_youth_by_age, is_adult_by_age)
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
        elif is_youth_by_age and not is_adult_by_age and unit_type == 'Adult':
            # Only flag as error for EU customers (is_adult_by_age=False for EU youth)
            # For non-EU, is_adult_by_age=True for 18+, so this won't trigger
            # Non-EU youth bookings are expected to become Adult (no error, light yellow color)
            errors.append(f"Youth {name} (age {age:.1f}) booked as Adult")
        elif is_adult_by_age and unit_type == 'Child':
            errors.append(f"Adult {name} (age {age:.1f}) booked as Child ")
        elif not is_youth_by_age and unit_type == 'Youth':
            # Youth unit but age is outside youth range (18-24)
            if is_child_by_age:
                errors.append(f"Child {name} (age {age:.1f}) booked as Youth")
            elif is_adult_by_age:
                errors.append(f"Adult {name} (age {age:.1f}) booked as Youth")
            else:
                errors.append(f"Youth unit {name} (age {age:.1f}) is outside 18-24 range")
    
    return errors

