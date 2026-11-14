"""
Duplicate name detection within bookings.

Names are normalized before comparison, so a duplicate is caught regardless of
letter case, accents, punctuation or word order. Unit type indicators like
"(Adult)" or "(Child)" are stripped first.
"""

import logging
from collections import Counter, defaultdict

from utils.normalization import (
    name_comparison_key,
    normalize_name,
    strip_unit_suffix,
)

logger = logging.getLogger(__name__)


def check_duplicates_in_booking(travelers_list):
    """
    Check for duplicate names within a booking.

    Two names count as duplicates when their normalized parts match in any
    order, which covers:
    - Identical names ("John Smith" / "John Smith")
    - Case differences ("Lianne George" / "lianne George")
    - Accent and punctuation differences ("José García" / "Jose Garcia")
    - Swapped first/last name order ("Lianne George" / "George Lianne")
    - The same person booked under different unit types ("(Adult)"/"(Child)")

    Args:
        travelers_list: List of traveler dicts with 'name' key

    Returns:
        tuple: (has_duplicates: bool, duplicate_names: list)
               Duplicate names are returned as originally written, in booking
               order, so callers can match them back to their rows.

    Example:
        travelers = [
            {'name': 'John Smith (Adult)'},
            {'name': 'Smith John (Child)'},
            {'name': 'Jane Doe'}
        ]
        -> (True, ['John Smith (Adult)', 'Smith John (Child)'])
    """
    if not travelers_list:
        return False, []

    # Pair each name with an order-insensitive comparison key.
    names_in_booking = []
    for traveler in travelers_list:
        full_name = str(traveler.get('name', '')).strip()
        if not full_name:
            continue

        base_name = strip_unit_suffix(full_name)
        key = name_comparison_key(base_name)
        if not key:
            # Nothing comparable left (e.g. punctuation-only name);
            # name content validation reports these separately.
            continue

        names_in_booking.append((key, base_name, full_name))

    key_counts = Counter(key for key, _, _ in names_in_booking)

    duplicate_names = []
    for key, _, full_name in names_in_booking:
        if key_counts[key] > 1 and full_name not in duplicate_names:
            duplicate_names.append(full_name)

    if not duplicate_names:
        return False, []

    _log_duplicate_groups(names_in_booking, key_counts)

    return True, duplicate_names


def _log_duplicate_groups(names_in_booking, key_counts):
    """
    Log each duplicate group and whether it matched exactly or by variation.

    Helps tell a straight repeat apart from a reordered or re-cased name when
    reviewing why a booking was flagged.
    """
    groups = defaultdict(list)
    for key, base_name, full_name in names_in_booking:
        if key_counts[key] > 1:
            groups[key].append((base_name, full_name))

    for members in groups.values():
        normalized = {normalize_name(base_name) for base_name, _ in members}
        match_type = 'exact' if len(normalized) == 1 else 'variation'
        flagged = [full_name for _, full_name in members]
        logger.info(f"Found duplicate names in booking ({match_type} match): {flagged}")


def get_duplicate_error_message(duplicate_names):
    """
    Generate error message for duplicate names.

    Args:
        duplicate_names: List of duplicate name strings

    Returns:
        str: Error message
    """
    return f"Duplicated names in the booking: {', '.join(duplicate_names)}"
