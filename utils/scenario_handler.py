"""
Scenario Handler for Name Extraction

Handles different file combination scenarios:
1. Ventrata only
2. Ventrata + Monday
3. Update + Ventrata (future)
4. Update + Ventrata + Monday (future)
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingScenario(Enum):
    """Enumeration of processing scenarios."""
    VENTRATA_ONLY = "ventrata_only"
    VENTRATA_MONDAY = "ventrata_monday"
    UPDATE_VENTRATA = "update_ventrata"  # Future
    UPDATE_VENTRATA_MONDAY = "update_ventrata_monday"  # Future


def determine_scenario(ventrata_df, monday_df=None, update_df=None):
    """
    Determine the processing scenario based on available data files.
    
    Args:
        ventrata_df: Ventrata DataFrame (required)
        monday_df: Monday DataFrame (optional)
        update_df: Update DataFrame (optional, future)
        
    Returns:
        ProcessingScenario: The determined scenario
    """
    has_ventrata = ventrata_df is not None and not ventrata_df.empty
    has_monday = monday_df is not None and not monday_df.empty
    has_update = update_df is not None and not update_df.empty
    
    if not has_ventrata:
        raise ValueError("Ventrata file is required")
    
    # Future scenarios
    if has_update and has_monday:
        return ProcessingScenario.UPDATE_VENTRATA_MONDAY
    elif has_update:
        return ProcessingScenario.UPDATE_VENTRATA
    
    # Current scenarios
    if has_monday:
        return ProcessingScenario.VENTRATA_MONDAY
    else:
        return ProcessingScenario.VENTRATA_ONLY


def get_monday_columns(scenario):
    """
    Get list of Monday-specific columns to include based on scenario.
    
    Args:
        scenario: ProcessingScenario enum value
        
    Returns:
        list: List of column names to include
    """
    if scenario == ProcessingScenario.VENTRATA_MONDAY:
        return ['PNR', 'Ticket Group', 'TIX NOM']
    elif scenario == ProcessingScenario.UPDATE_VENTRATA_MONDAY:
        return ['PNR', 'Ticket Group', 'TIX NOM']  # Future: may add more
    else:
        return []


def should_include_monday_columns(scenario):
    """
    Check if Monday-specific columns should be included.
    
    Args:
        scenario: ProcessingScenario enum value
        
    Returns:
        bool: True if Monday columns should be included
    """
    return scenario in [
        ProcessingScenario.VENTRATA_MONDAY,
        ProcessingScenario.UPDATE_VENTRATA_MONDAY
    ]

