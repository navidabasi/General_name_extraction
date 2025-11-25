import re
from typing import List, Optional, Dict, Tuple

import pandas as pd

UNIT_KEYWORD_MAP = {
    'adult': 'Adult',
    'child': 'Child',
    'youth': 'Youth',
    'infant': 'Infant',
}

_NAM_CONF_PATTERN = re.compile(r'nam\s+conf\.?\s*(.*)', re.IGNORECASE | re.DOTALL)
_LINE_PATTERN = re.compile(r'^(.*?)(?:\s*\(([^)]+)\))?\s*$', re.DOTALL)

def parse_private_notes_template(private_notes: Optional[str]) -> List[Dict[str, Optional[str]]]:
    """
    Parses the private notes to extract names and unit types given after
    NAM CONF phrase.

    Args:
        private_notes: Raw string from Ventrata private notes column.

    Returns:
        List of dictionaries with keys:
        - name ( str ): traveler name extracted from the line
        - unity_type ( str | None ): mapped unit type if a keyword was provided if not would be adult
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

        line_match = _LINE_PATTERN.match(line)
        if not line_match:
            parsed.append({'name': line, 'unit_type': None})
            continue

        clean_name = line_match.group(1).strip(" -•\t")
        unit_token = (line_match.group(2) or '').strip().lower()
        unit_type = UNIT_KEYWORD_MAP.get(unit_token)

        if clean_name:
            parsed.append({'name': clean_name, 'unit_type': unit_type})

    return parsed


def build_travelers_from_private_notes(
    private_notes: Optional[str],
    ventrata_rows: Optional[pd.DataFrame],
    unit_column: Optional[str]
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
        if parsed_unit:
            unit_type = parsed_unit
        elif unit_idx < len(booking_units):
            unit_type = booking_units[unit_idx]
            unit_idx += 1
            missing_template_unit = True
        else:
            unit_type = None
            missing_template_unit = True

        travelers.append({
            'name': name,
            'unit_type': unit_type,
            'original_unit_type': unit_type
        })

    return travelers, missing_template_unit

        

