"""
Utility functions for data normalization and transformation.
"""

from .normalization import (
    normalize_ref,
    normalize_time,
    extract_language_from_product_code,
    extract_tour_type_from_product_code,
    standardize_column_names,
    get_column_value
)

from .age_calculator import (
    parse_dob,
    calculate_age_on_travel_date,
    calculate_age_from_dob,
    calculate_age_flags,
    categorize_age,
    convert_infant_to_child_by_product_tags,
    convert_infant_to_child_for_colosseum  # Backward compatibility
)

from .tix_nom_generator import generate_tix_nom

from .scenario_handler import (
    determine_scenario,
    should_include_monday_columns,
    get_monday_columns,
    ProcessingScenario
)

__all__ = [
    'normalize_ref',
    'normalize_time',
    'extract_language_from_product_code',
    'extract_tour_type_from_product_code',
    'standardize_column_names',
    'get_column_value',
    'parse_dob',
    'calculate_age_on_travel_date',
    'calculate_age_from_dob',
    'calculate_age_flags',
    'categorize_age',
    'convert_infant_to_child_by_product_tags',
    'convert_infant_to_child_for_colosseum',  # Backward compatibility
    'generate_tix_nom',
    'determine_scenario',
    'should_include_monday_columns',
    'get_monday_columns',
    'ProcessingScenario'
]

