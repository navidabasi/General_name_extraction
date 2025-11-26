import re
import logging
from typing import List, Optional, Dict, Tuple

import pandas as pd

from utils.age_calculator import calculate_age_on_travel_date, categorize_age

logger = logging.getLogger(__name__)



UNIT_KEYWORD_MAP = {
    'adult': 'Adult',
    'adl': 'Adult',
    'ad': 'Adult',
    'child': 'Child',
    'chl': 'Child',
    'kid': 'Child',
    'youth': 'Youth',
    'yth': 'Youth',
    'infant': 'Infant',
    'inf': 'Infant',
    'baby': 'Infant',
}

_NAM_CONF_PATTERN = re.compile(
    r'(?:[-–—]?\s*)?(?:dash\s+)?na(?:m)?[\s\.\-]*conf\.?[:\s]*(.*)',
    re.IGNORECASE | re.DOTALL
)
_LINE_PATTERN = re.compile(r'^(.*?)(?:\s*\(([^)]+)\))?\s*$', re.DOTALL)
_DOB_PATTERN = re.compile(
    r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})'
)
# Pattern to extract "age XX" format (e.g., "age 44", "Age: 23", "edad 10", "âge 5")
_AGE_KEYWORD_PATTERN = re.compile(
    r'\b(?:age|edad|âge|alter|età|leeftijd|wiek|возраст)[:\s]*(\d{1,3})\b',
    re.IGNORECASE
)
# Pattern to extract direct age values like "23 years", "12 anos", "5 ans", "7 Jahre"
_AGE_SUFFIX_PATTERN = re.compile(
    r'\b(\d{1,3})\s*(?:years?|yrs?|años?|anos?|ans?|jahre?|jaar|lat|лет|rok[uów]?|år)\b',
    re.IGNORECASE
)
# Pattern to extract just a number at end of line (fallback): "John Doe 23"
_AGE_NUMBER_ONLY_PATTERN = re.compile(
    r'\s(\d{1,3})\s*$'
)


def parse_private_notes_template(private_notes: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """
    Parses the private notes to extract names and unit types given after
    NAM CONF phrase.
    Used for duplicated names, DOB missing on GYG bookings and as a fallback for name extraction.

    Supports:
    - DOB formats: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, DD.MM.YYYY, "15 March 2000"
    - Direct age: "23 years", "12", "10 anos", "5 ans", "7 Jahre", etc.
    - Unit type keywords in parentheses: (Adult), (Child), (Youth), (Infant)

    Args:
        private_notes: Raw string from Ventrata private notes column.

    Returns:
        List of dictionaries with keys:
        - name (str): traveler name extracted from the line
        - unit_type (str | None): mapped unit type if a keyword was provided
        - dob (str | None): date of birth if found
        - direct_age (int | None): direct age value if found (e.g., "23 years")
    """

    if not private_notes:
        return []

    match = _NAM_CONF_PATTERN.search(str(private_notes))
    if not match:
        return []

    block = match.group(1)
    parsed = []

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        dob_value = None
        direct_age = None
        
        # First try to extract DOB (e.g., "28/7/1980", "1980-07-28", "15 March 2000")
        dob_match = _DOB_PATTERN.search(line)
        if dob_match:
            dob_value = dob_match.group(1).strip()
            start, end = dob_match.span(1)
            prefix = line[:start].rstrip(" -:;")
            suffix = line[end:].lstrip(" -:;")
            line = f"{prefix} {suffix}".strip()
            logger.debug(f"Extracted DOB: {dob_value} from line, clean name: {line}")
        else:
            # No DOB found, try to extract direct age
            # Priority: "age 44" > "23 years" > just "23" at end
            
            # Try "age 44", "Age: 23", "edad 10" pattern first
            age_match = _AGE_KEYWORD_PATTERN.search(line)
            if age_match:
                try:
                    age_val = int(age_match.group(1))
                    if 0 <= age_val <= 120:
                        direct_age = age_val
                        # Remove the entire "age XX" part from the line
                        line = line[:age_match.start()].rstrip(" -:;") + line[age_match.end():].lstrip(" -:;")
                        line = line.strip()
                        logger.debug(f"Extracted age with keyword: {direct_age}, clean name: {line}")
                except ValueError:
                    pass
            
            # Try "23 years", "10 anos" pattern
            if direct_age is None:
                age_match = _AGE_SUFFIX_PATTERN.search(line)
                if age_match:
                    try:
                        age_val = int(age_match.group(1))
                        if 0 <= age_val <= 120:
                            direct_age = age_val
                            line = line[:age_match.start()].rstrip(" -:;") + line[age_match.end():].lstrip(" -:;")
                            line = line.strip()
                            logger.debug(f"Extracted age with suffix: {direct_age}, clean name: {line}")
                    except ValueError:
                        pass
            
            # Try just a number at end: "John Doe 23"
            if direct_age is None:
                age_match = _AGE_NUMBER_ONLY_PATTERN.search(line)
                if age_match:
                    try:
                        age_val = int(age_match.group(1))
                        if 0 <= age_val <= 120:
                            direct_age = age_val
                            line = line[:age_match.start()].rstrip(" -:;")
                            logger.debug(f"Extracted age number only: {direct_age}, clean name: {line}")
                    except ValueError:
                        pass

        line_match = _LINE_PATTERN.match(line)
        if not line_match:
            parsed.append({'name': line, 'unit_type': None, 'dob': dob_value, 'direct_age': direct_age})
            continue

        clean_name = line_match.group(1).strip(" -•\t:") if line_match.group(1) else ''
        unit_token = (line_match.group(2) or '').strip().lower()
        unit_type = UNIT_KEYWORD_MAP.get(unit_token)

        if clean_name:
            parsed.append({'name': clean_name, 'unit_type': unit_type, 'dob': dob_value, 'direct_age': direct_age})

    return parsed


def build_travelers_from_private_notes(
    private_notes: Optional[str],
    ventrata_rows: Optional[pd.DataFrame],
    unit_column: Optional[str],
    travel_date: Optional[str] = None
) -> Tuple[List[Dict[str, Optional[str]]], bool]:
    """
    Create traveler dicts from the NAM CONF template, optionally matching booking units if the unit type failed to be extracted.

    Args:
        private_notes: Raw string from Ventrata private notes column.
        ventrata_rows: Booking rows (DataFrame) to pull unit info from.
        unit_column: Column name for units inside ventrata_rows.

    Returns:
        tuple(list[dict], bool): Travelers and flag indicating missing unit keywords.
    """
    template_entries = parse_private_notes_template(private_notes)
    if not template_entries:
        return [], False

    booking_units: List[str] = []
    if ventrata_rows is not None and unit_column and unit_column in ventrata_rows.columns:
        for value in ventrata_rows[unit_column]:
            if pd.notna(value):
                value_str = str(value).strip()
                if value_str:
                    booking_units.append(value_str)

    travelers: List[Dict[str, Optional[str]]] = []
    unit_idx = 0
    missing_template_unit = False

    for entry in template_entries:
        name = entry.get('name')
        if not name:
            continue

        parsed_unit = entry.get('unit_type')
        dob_value = entry.get('dob')
        direct_age = entry.get('direct_age')
        age_value = None
        age_unit = None

        # Priority: DOB > direct age > unit keyword > booking units
        if dob_value and travel_date:
            age_value = calculate_age_on_travel_date(dob_value, travel_date)
            age_unit = categorize_age(age_value)
        elif direct_age is not None:
            # Use direct age value (e.g., "23 years", "12", "10 anos")
            age_value = float(direct_age)
            age_unit = categorize_age(age_value)
            logger.debug(f"Using direct age {direct_age} for {name}, categorized as {age_unit}")

        unit_type = parsed_unit
        if age_unit:
            if parsed_unit and parsed_unit != age_unit:
                logger.info(f"Private notes age/unit mismatch for {name}: template={parsed_unit}, age-based={age_unit}")
            unit_type = age_unit

        if not unit_type:
            if unit_idx < len(booking_units):
                unit_type = booking_units[unit_idx]
                unit_idx += 1
                missing_template_unit = True
            else:
                unit_type = None
                missing_template_unit = True

        traveler_entry = {
            'name': name,
            'unit_type': unit_type,
            'original_unit_type': unit_type,
            'dob': dob_value,
            'age': age_value,
        }

        travelers.append(traveler_entry)

    return travelers, missing_template_unit


def supplement_travelers_with_private_notes(
    travelers: List[Dict],
    private_notes: Optional[str],
    travel_date: Optional[str] = None,
    ventrata_rows: Optional[pd.DataFrame] = None,
    unit_column: Optional[str] = None
) -> List[Dict]:
    """
    Supplement or replace GYG travelers with data from private notes when DOBs are missing.
    
    When GYG Standard/MDA extraction succeeds but travelers are missing DOBs,
    this function replaces the entire traveler list with data from private notes
    if available. This ensures correct unit type assignment and ID mapping.
    
    Args:
        travelers: List of traveler dicts from GYG extraction
        private_notes: Raw private notes string
        travel_date: Travel date for age calculation
        ventrata_rows: Booking rows (DataFrame) to pull unit info from
        unit_column: Column name for units inside ventrata_rows
        
    Returns:
        list: Travelers from private notes if DOBs were missing, otherwise original travelers
    """
    if not travelers or not private_notes:
        return travelers
    
    # Check if any travelers are missing age data
    missing_age_count = sum(1 for t in travelers if t.get('age') is None)
    if missing_age_count == 0:
        logger.debug("All travelers have age data, no replacement needed")
        return travelers
    
    logger.info(f"{missing_age_count}/{len(travelers)} travelers missing age data, checking private notes")
    
    # Try to build travelers from private notes
    private_notes_travelers, missing_units = build_travelers_from_private_notes(
        private_notes, ventrata_rows, unit_column, travel_date
    )
    
    if not private_notes_travelers:
        logger.debug("No NAM CONF template found in private notes, keeping original travelers")
        return travelers
    
    # Check if private notes has same number of travelers
    if len(private_notes_travelers) != len(travelers):
        logger.warning(
            f"Private notes traveler count ({len(private_notes_travelers)}) doesn't match "
            f"GYG extraction ({len(travelers)}), keeping original travelers"
        )
        return travelers
    
    # Check if private notes travelers have age/unit data
    pn_with_age = sum(1 for t in private_notes_travelers if t.get('age') is not None)
    pn_with_unit = sum(1 for t in private_notes_travelers if t.get('unit_type') is not None)
    
    # Replace if private notes has more age data or unit types
    if pn_with_age > (len(travelers) - missing_age_count) or pn_with_unit == len(private_notes_travelers):
        logger.info(
            f"Replacing GYG travelers with private notes data: "
            f"{pn_with_age} have age, {pn_with_unit} have unit types"
        )
        return private_notes_travelers
    
    # Fallback: try to supplement individual travelers by name matching
    def normalize_name(name):
        if not name:
            return ''
        return ' '.join(name.lower().split())
    
    template_lookup = {}
    for entry in private_notes_travelers:
        name = entry.get('name')
        if name:
            norm_name = normalize_name(name)
            template_lookup[norm_name] = entry
    
    supplemented_count = 0
    for traveler in travelers:
        if traveler.get('age') is not None:
            continue  # Already has age
        
        traveler_name = traveler.get('name', '')
        norm_name = normalize_name(traveler_name)
        
        if norm_name not in template_lookup:
            continue
        
        entry = template_lookup[norm_name]
        
        # Supplement age from DOB or direct age
        if entry.get('age') is not None:
            traveler['age'] = entry['age']
            if entry.get('dob'):
                traveler['dob'] = entry['dob']
            logger.info(f"Supplemented age for {traveler_name}: age={entry['age']}")
            supplemented_count += 1
        
        # Supplement unit type if available
        if entry.get('unit_type') and not traveler.get('unit_type'):
            traveler['unit_type'] = entry['unit_type']
            traveler['original_unit_type'] = entry.get('original_unit_type', entry['unit_type'])
            logger.debug(f"Supplemented unit type for {traveler_name}: {entry['unit_type']}")
    
    if supplemented_count > 0:
        logger.info(f"Supplemented {supplemented_count} travelers with private notes data")
    
    return travelers

