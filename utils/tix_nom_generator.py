"""
TIX NOM Generator

Generates TIX NOM (Ticket Nomination) strings from PNR values.

Format: (TIX NOM HH:MM TICKET_TYPE COMPANY_CODE)

Example:
- PNR: RFT20251121A1200 → (TIX NOM 12:00 ARENA RFT)
- PNR: C20251121R0900 → (TIX NOM 09:00 REG C)
"""

import re
import pandas as pd
import logging

from config import COMPANY_CODE_MAP, TICKET_TYPE_MAP

logger = logging.getLogger(__name__)


def parse_pnr_for_tix_nom(pnr_value):
    """
    Parse PNR value to extract components for TIX NOM generation.
    
    PNR Format: COMPANY_CODE + YYYYMMDD + TICKET_TYPE + TIME
    
    Examples:
    - RFT20251121A1200 → company: RFT, date: 20251121, type: A, time: 1200
    - C20251121R0900 → company: C, date: 20251121, type: R, time: 0900
    
    The company code is the first letters before the year (number indicators).
    Ticket type is A, AA, or R (after the date).
    Ticket time is the last 4 digits.
    
    Args:
        pnr_value: PNR string value
        
    Returns:
        dict: {
            'company_code': str,  # e.g., 'RFT', 'C'
            'ticket_type': str,    # e.g., 'A', 'AA', 'R'
            'time': str,          # e.g., '1200', '0900'
            'time_formatted': str  # e.g., '12:00', '09:00'
        } or None if parsing fails
    """
    if not pnr_value or pd.isna(pnr_value):
        return None
    
    pnr_str = str(pnr_value).strip()
    
    # Pattern: COMPANY_CODE (letters) + YYYYMMDD (8 digits) + TICKET_TYPE (A/AA/R/UG) + TIME (4 digits)
    # Examples:
    # - RFT20251121A1200 → RFT + 20251121 + A + 1200
    # - C20251121R0900 → C + 20251121 + R + 0900
    # - GC20251121AA1430 → GC + 20251121 + AA + 1430
    # - MC20260207UG1245 → MC + 20260207 + UG + 1245
    
    # Primary pattern: letters + 8 digits + A/AA/R/UG + 4 digits
    pattern = r'^([A-Za-z]+)(\d{8})(A{1,2}|R|UG)(\d{4})$'
    match = re.match(pattern, pnr_str)
    
    if not match:
        # Try alternative pattern with separators
        pattern_alt = r'^([A-Za-z]+)[-\s]?(\d{8})[-\s]?(A{1,2}|R|UG)[-\s]?(\d{4})$'
        match = re.match(pattern_alt, pnr_str)
    
    if match:
        company_code = match.group(1).upper()
        date_str = match.group(2)  # YYYYMMDD (not used in TIX NOM but extracted)
        ticket_type = match.group(3).upper()
        time_str = match.group(4)  # HHMM format (last 4 digits)
        
        # Format time as HH:MM (remove leading zero if hour is single digit, but keep format)
        if len(time_str) == 4:
            hour = time_str[:2]
            minute = time_str[2:]
            # Format: HH:MM (keep leading zero for hour if needed)
            time_formatted = f"{hour}:{minute}"
        else:
            time_formatted = time_str
        
        return {
            'company_code': company_code,
            'ticket_type': ticket_type,
            'time': time_str,
            'time_formatted': time_formatted
        }
    
    # Fallback: try to extract what we can
    logger.warning(f"Could not parse PNR format: {pnr_str}")
    return None


def map_ticket_type(ticket_type):
    """
    Map ticket type code to display name using TICKET_TYPE_MAP from config.
    
    Args:
        ticket_type: Ticket type code (e.g. 'A', 'AA', 'R', 'UG')
        
    Returns:
        str: Display name from config, or original code uppercase if not in map
    """
    if not ticket_type:
        return ''
    code_upper = ticket_type.upper()
    return TICKET_TYPE_MAP.get(code_upper, code_upper)


def map_company_code(company_code):
    """
    Map company code to display name using COMPANY_CODE_MAP.
    
    Args:
        company_code: Company code from PNR (e.g., 'RFT', 'C', 'GC')
        
    Returns:
        str: Display name (e.g., 'RFT', 'C-CALL', 'G-CALL')
    """
    if not company_code:
        return ''
    
    company_code_upper = company_code.upper()
    
    # Check COMPANY_CODE_MAP first
    if company_code_upper in COMPANY_CODE_MAP:
        return COMPANY_CODE_MAP[company_code_upper]
    
    # Return original if not in map
    return company_code_upper


def generate_tix_nom(pnr_value):
    """
    Generate TIX NOM string from PNR value.
    
    Format: (TIX NOM HH:MM TICKET_TYPE COMPANY_CODE)
    
    Examples:
    - RFT20251121A1200 → (TIX NOM 12:00 ARENA RFT)
    - C20251121R0900 → (TIX NOM 09:00 REG C)
    - GC20251121AA1430 → (TIX NOM 14:30 ARENA24 G-CALL)
    
    Args:
        pnr_value: PNR string value
        
    Returns:
        str: Generated TIX NOM string in format "(TIX NOM HH:MM TICKET_TYPE COMPANY_CODE)"
              or empty string if PNR cannot be parsed
    """
    if not pnr_value or pd.isna(pnr_value):
        return ''
    
    # Parse PNR
    pnr_info = parse_pnr_for_tix_nom(pnr_value)
    
    if not pnr_info:
        logger.debug(f"Could not generate TIX NOM from PNR: {pnr_value}")
        return ''
    
    # Map ticket type
    ticket_type_display = map_ticket_type(pnr_info['ticket_type'])
    
    # Map company code
    company_display = map_company_code(pnr_info['company_code'])
    
    # Build TIX NOM string
    tix_nom = f"(TIX NOM {pnr_info['time_formatted']} {ticket_type_display} {company_display})"
    
    logger.debug(f"Generated TIX NOM: {tix_nom} from PNR: {pnr_value}")
    
    return tix_nom

