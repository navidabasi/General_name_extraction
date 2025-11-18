"""
Data normalization utilities.

Handles normalization of:
- Order references (removing separators, whitespace)
- Time values (converting to HH:MM format)
- Product codes (extracting language and tour type)
- Column names (case-insensitive access)
"""

import re
import pandas as pd
import logging

from config import LANGUAGE_MAP, TOUR_TYPE_PATTERNS

logger = logging.getLogger(__name__)


def normalize_ref(ref):
    """
    Normalize order reference to handle format variations.
    
    Removes:
    - All whitespace
    - Common separators (hyphens, underscores, dots, slashes)
    - Non-alphanumeric characters
    
    Args:
        ref: Order reference string
        
    Returns:
        str: Normalized lowercase reference
        
    Example:
        "ABC-123 456" -> "abc123456"
    """
    if pd.isna(ref) or ref is None:
        return ""
    
    ref_str = str(ref).lower()
    ref_str = re.sub(r'\s+', '', ref_str)
    ref_str = re.sub(r'[-_.\\/]', '', ref_str)  
    ref_str = re.sub(r'[^a-z0-9]', '', ref_str)
    
    return ref_str


def normalize_time(time_value):
    """
    Normalize time to HH:MM format.
    
    Handles multiple input formats:
    - HH:MM (already normalized)
    - HH:MM:SS (strips seconds)
    - 12-hour format with AM/PM
    - 24-hour format without colon (e.g., 1430 -> 14:30)
    - Excel decimal format (0.5 -> 12:00)
    
    Args:
        time_value: Time in various formats
        
    Returns:
        str: Time in HH:MM format, or empty string if parsing fails
        
    Example:
        "2:30 PM" -> "14:30"
        "1430" -> "14:30"
        "09:05:00" -> "09:05"
    """
    if pd.isna(time_value) or time_value is None:
        return ""
    
    time_str = str(time_value).strip()
    if not time_str or time_str.lower() in ['nan', 'n/a', 'na']:
        return ""
    
    try:
        # Handle HH:MM format
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            return f"{hours:02d}:{minutes:02d}"
        
        # Handle HH:MM:SS format
        if re.match(r'^\d{1,2}:\d{2}:\d{2}$', time_str):
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            return f"{hours:02d}:{minutes:02d}"
        
        # Handle time with AM/PM
        am_pm_match = re.match(r'^(\d{1,2}):?(\d{0,2})\s*(AM|PM)$', time_str.upper())
        if am_pm_match:
            hours = int(am_pm_match.group(1))
            minutes = int(am_pm_match.group(2)) if am_pm_match.group(2) else 0
            period = am_pm_match.group(3)
            
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            
            return f"{hours:02d}:{minutes:02d}"
        
        # Handle 24-hour format without colon (e.g., 1430 for 14:30)
        if re.match(r'^\d{3,4}$', time_str):
            if len(time_str) == 3:
                hours = int(time_str[0])
                minutes = int(time_str[1:3])
            else:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
            
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return f"{hours:02d}:{minutes:02d}"
        
    except (ValueError, IndexError):
        pass
    
    # If we can't parse it, log and return empty
    logger.warning(f"Could not normalize time: {time_str}")
    return ""


def extract_language_from_product_code(product_code):
    """
    Extract language from product code (last 3 characters).
    
    Args:
        product_code: Product code string (e.g., "ROMCOL-ENG")
        
    Returns:
        str: Language name or language code if not mapped
        
    Example:
        "ROMCOL-ENG" -> "English"
        "ROMARN-SPA" -> "Spanish"
    """
    if pd.isna(product_code) or product_code is None:
        return ""
    
    product_code_str = str(product_code).strip().upper()
    if len(product_code_str) < 3:
        return ""
    
    # Get last 3 characters
    lang_code = product_code_str[-3:]
    
    return LANGUAGE_MAP.get(lang_code, lang_code) #Config file mapping


def extract_tour_type_from_product_code(product_code):
    """
    Extract tour type from product code patterns.
    
    Args:
        product_code: Product code string
        
    Returns:
        str: Tour type name or empty string
        
    Example:
        "ROMARNSML-ENG" -> "Arena Small"
        "ROMCOL-SPA" -> "Regular"
    """
    if pd.isna(product_code) or product_code is None:
        return ""
    
    product_code_str = str(product_code).strip().upper()
    
    # Check patterns in order (most specific first)
    for pattern, tour_type in TOUR_TYPE_PATTERNS.items():
        if pattern in product_code_str:
            return tour_type
    
    return ""


def standardize_column_names(df):
    """
    Create a case-insensitive column mapping for a DataFrame.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        dict: Mapping from lowercase column names to actual column names
        
    Example:
        {"order reference": "Order Reference", "unit": "UNIT"}
    """
    column_map = {}
    for col in df.columns:
        column_map[col.lower()] = col
    return column_map


def get_column_value(row, column_map, *possible_names):
    """
    Get value from row using case-insensitive column lookup.
    
    Args:
        row: DataFrame row (Series)
        column_map: Dict mapping lowercase names to actual column names
        *possible_names: Possible column name variations
        
    Returns:
        Value from the first matching column, or None
        
    Example:
        get_column_value(row, col_map, 'Order Reference', 'order_reference')
    """
    for name in possible_names:
        actual_col = column_map.get(name.lower())
        if actual_col:
            return row.get(actual_col)
    return None

