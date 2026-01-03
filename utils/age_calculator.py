"""
Age calculation utilities.

Handles:
- DOB parsing (multiple formats)
- Age calculation on specific travel dates
- Age categorization (Child, Youth, Adult)
- Unit type conversion based on product tags
"""

from datetime import datetime
import pandas as pd
import logging

from config import AGE_CHILD_MAX, AGE_YOUTH_MIN, AGE_YOUTH_MAX, AGE_ADULT_MIN
from config import UNIT_TYPE_ADULT, UNIT_TYPE_CHILD, UNIT_TYPE_YOUTH, UNIT_TYPE_INFANT

logger = logging.getLogger(__name__)


def parse_dob(dob_str):
    """
    Parse date of birth string into datetime object.
    
    Supports multiple formats:
    - DD/MM/YYYY (e.g., "15/03/1990")
    - YYYY-MM-DD (e.g., "1990-03-15")
    - DD-MM-YYYY (e.g., "15-03-1990")
    - DD.MM.YYYY (e.g., "15.03.1990")
    
    Args:
        dob_str: Date of birth string
        
    Returns:
        datetime.date: Parsed date object, or None if parsing fails
    """
    if not dob_str or pd.isna(dob_str):
        return None
    
    dob_str = str(dob_str).strip()
    
    # Try different date formats
    formats = [
        '%d/%m/%Y',  # DD/MM/YYYY
        '%Y-%m-%d',  # YYYY-MM-DD
        '%d-%m-%Y',  # DD-MM-YYYY
        '%d.%m.%Y',  # DD.MM.YYYY
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dob_str, fmt).date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse DOB: {dob_str}")
    return None


def calculate_age_on_travel_date(dob_str, travel_date_str):
    """
    Calculate age in years on a specific travel date.
    
    Args:
        dob_str: Date of birth string (multiple formats supported)
        travel_date_str: Travel date string or datetime object
        
    Returns:
        float: Age in years, or None if calculation fails
        
    Example:
        ("15/03/1990", "01/06/2024") -> 34.2
    """
    try:
        # Parse DOB
        dob_obj = parse_dob(dob_str)
        if dob_obj is None:
            return None
        
        # Parse travel date
        if isinstance(travel_date_str, str):
            travel_date_obj = pd.to_datetime(travel_date_str).date()
        else:
            travel_date_obj = pd.to_datetime(travel_date_str).date()
        
        # Calculate age
        age = travel_date_obj.year - dob_obj.year
        
        # Check if birthday has been reached this year or not
        if (travel_date_obj.month < dob_obj.month or 
            (travel_date_obj.month == dob_obj.month and travel_date_obj.day < dob_obj.day)):
            age -= 1
        
        return float(age)
        
    except Exception as e:
        logger.warning(f"Error calculating age for DOB {dob_str}, travel date {travel_date_str}: {e}")
        return None


def categorize_age(age):
    """
    Categorize age into Child, Youth, or Adult.
    
    Age categories:
    - Child: < 18 years
    - Youth: 18-25 years (inclusive)
    - Adult: > 25 years
    
    Args:
        age: Age in years (float or int)
        
    Returns:
        str: 'Child', 'Youth', or 'Adult'
    """
    if age is None:
        return None
    
    if age < AGE_CHILD_MAX:
        return UNIT_TYPE_CHILD
    elif AGE_YOUTH_MIN <= age < AGE_YOUTH_MAX:
        return UNIT_TYPE_YOUTH
    else:
        return UNIT_TYPE_ADULT


def calculate_age_flags(age, customer_country=None):
    """
    Calculate age category flags (is_child_by_age, is_youth_by_age, is_adult_by_age)
    based on age and customer country.
    
    Adult detection rules:
    - EU countries: Adult is >= 25 years
    - Non-EU countries: Adult is >= 18 years
    
    Args:
        age: Age in years (float or int), or None
        customer_country: Customer country string (optional, defaults to EU rules if None)
        
    Returns:
        dict: {
            'is_child_by_age': bool,
            'is_youth_by_age': bool,
            'is_adult_by_age': bool
        }
    """
    from validators import is_eu_country
    
    if age is None:
        return {
            'is_child_by_age': False,
            'is_youth_by_age': False,
            'is_adult_by_age': False
        }
    
    # Determine if EU country (default to EU if country not provided)
    is_eu = is_eu_country(customer_country) if customer_country else True
    
    # Calculate flags
    is_child_by_age = age < AGE_CHILD_MAX
    is_youth_by_age = AGE_YOUTH_MIN <= age < AGE_YOUTH_MAX
    
    # Adult detection: EU >= 25, Non-EU >= 18
    if is_eu:
        is_adult_by_age = age >= AGE_ADULT_MIN  # EU: >= 25
    else:
        is_adult_by_age = age >= AGE_CHILD_MAX  # Non-EU: >= 18
    
    return {
        'is_child_by_age': is_child_by_age,
        'is_youth_by_age': is_youth_by_age,
        'is_adult_by_age': is_adult_by_age
    }


def calculate_age_from_dob(dob_str, reference_date, date_format='%d/%m/%Y'):
    """
    Calculate age from DOB string using a reference date (e.g., travel date or current date).
    
    This is the centralized function for all age calculations from DOB strings.
    Used by extractors (GYG MDA, GYG Standard, etc.) to calculate traveler ages.
    
    Note: This function only returns age. Age flags (is_child_by_age, etc.) should be
    calculated later using calculate_age_flags() once customer country is known.
    
    Args:
        dob_str: Date of birth string (e.g., "15/03/1990")
        reference_date: Reference date for age calculation (datetime, pd.Timestamp, or str)
        date_format: Format of the DOB string (default: '%d/%m/%Y')
        
    Returns:
        dict: {'age': float} or {'age': None} if calculation fails
        
    Example:
        calculate_age_from_dob("15/03/1990", "2024-06-15")  # Using travel date
        -> {'age': 34.2}
    """
    try:
        # Parse DOB
        dob_date = pd.to_datetime(dob_str, format=date_format)
        
        # Parse reference date
        if isinstance(reference_date, str):
            ref_date = pd.to_datetime(reference_date)
        else:
            ref_date = pd.to_datetime(reference_date)
        
        # Calculate age in days, then convert to years
        age_days = (ref_date - dob_date).days
        age_value = float(age_days) / 365.25
        
        return {'age': age_value}
        
    except Exception as e:
        logger.debug(f"Could not calculate age from DOB {dob_str}: {e}")
        return {'age': None}


def convert_infant_to_child_for_colosseum(unit_type, product_tags):
    """
    Colosseum behaves same for Child and Infant, for simplicity we convert it to Child using product tags.
    The Product tags for our filter is just Colosseum but just in case I added some other keywords to be safe in other languages.
    Keywords checked: 'Colosseum', 'Colosseo', 'Kolosseo'
    
    Args:
        unit_type: Current unit type
        product_tags: Product tags string
        
    Returns:
        str: Converted unit type (Child if Infant and Colosseum, otherwise unchanged)
    """
    if unit_type != UNIT_TYPE_INFANT:
        return unit_type
    
    if not product_tags or pd.isna(product_tags):
        return unit_type
    
    product_tags_lower = str(product_tags).lower()
    colosseum_keywords = ['colosseum', 'colosseo', 'Kolosseum', 'Colisée']
    
    for keyword in colosseum_keywords:
        if keyword in product_tags_lower:
            logger.info(f"Converting Infant to Child for Colosseum booking (tags: {product_tags})")
            return UNIT_TYPE_CHILD
    
    return unit_type

