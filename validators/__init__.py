"""
Validation modules for name extraction.

Includes:
- Name content validation (forbidden keywords, digits, single letters)
- Duplicate name detection within bookings
- Youth/age validation
- Unit count vs traveler count validation
"""

from .name_validator import name_has_forbidden_issue, validate_name_content
from .duplicate_validator import check_duplicates_in_booking
from .youth_validator import validate_youth_booking, is_eu_country
from .unit_validator import (
    check_unit_traveler_mismatch,
    check_missing_dobs,
    check_all_under_18,
    check_only_child_infant,
    get_unit_counts
)

__all__ = [
    'name_has_forbidden_issue',
    'validate_name_content',
    'check_duplicates_in_booking',
    'validate_youth_booking',
    'is_eu_country',
    'check_unit_traveler_mismatch',
    'check_missing_dobs',
    'check_all_under_18',
    'check_only_child_infant',
    'get_unit_counts'
]

