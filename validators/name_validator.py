"""
Name content validation.

Checks for:
- Forbidden keywords in names
- Digits in names
- Single-letter first or last names
"""

import logging
from config import FORBIDDEN_NAME_KEYWORDS

logger = logging.getLogger(__name__)


def name_has_forbidden_issue(name):
    """
    Check if a name contains forbidden content.
    
    Forbidden content includes:
    1. Forbidden keywords ("Adult", "Child", "Client", "Traveler", "Travel", "Infant")
    2. Any digit characters
    3. Single-letter first or last name
    
    Args:
        name: Name string to check
        
    Returns:
        bool: True if name has issues, False otherwise
        
    Example:
        "Adult John" -> True (forbidden keyword)
        "John Smith123" -> True (contains digit)
        "J Smith" -> True (single letter first name)
        "John Smith" -> False (valid)
    """
    if not isinstance(name, str):
        return False
    
    name_lower = name.lower()
    
    # Check for forbidden keywords
    for keyword in FORBIDDEN_NAME_KEYWORDS:
        if keyword.lower() in name_lower:
            logger.debug(f"Name '{name}' contains forbidden keyword: {keyword}")
            return True
    
    # Check for any digit in the name
    if any(char.isdigit() for char in name):
        logger.debug(f"Name '{name}' contains digit")
        return True
    
    # Check for single-letter first or last name
    parts = name.strip().split()
    if len(parts) >= 2:
        if len(parts[0]) == 1 or len(parts[-1]) == 1:
            logger.debug(f"Name '{name}' has single-letter component")
            return True
    
    return False


def validate_name_content(names_list):
    """
    Validate content of all names in a list.
    
    Args:
        names_list: List of name strings
        
    Returns:
        list: List of names that have issues
        
    Example:
        ["John Smith", "Adult John", "Jane Doe"] -> ["Adult John"]
    """
    problematic_names = []
    
    for name in names_list:
        if name_has_forbidden_issue(name):
            problematic_names.append(name)
    
    if problematic_names:
        logger.info(f"Found {len(problematic_names)} names with content issues")
    
    return problematic_names

