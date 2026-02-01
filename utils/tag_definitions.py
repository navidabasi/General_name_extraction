"""
Tag definition helpers for Excel dropdowns.

Each definition maps product keywords to a list of tag options
that appear as dropdown choices (with associated colors).
"""

from typing import List, Dict

# Hex colors should be 6-character strings (no leading #)
TAG_DEFINITIONS = [
    {
        'keywords': [
            'castle',
            'castel',
            "sant'angelo",
            'sant angelo',
            'saint angelo',
            'romsan',
        ],
        'options': [
            {'label': 'Canceled', 'color': 'FF0000'},      # Red
            {'label': 'Use Cancele', 'color': 'FFC0CB'},   # Pink
            {'label': 'Waiting', 'color': 'A9A9A9'},       # Dark gray
            {'label': 'Use Waiting', 'color': 'FFBF00'},   # Amber
            {'label': 'Burned', 'color': 'BEBEBE'},        # Gray
            {'label': 'Missing Name', 'color': 'FFA500'},  # Orange
            {'label': 'Done', 'color': '69A750'},          # Grass green
            {'label': 'Extra', 'color': '2567f5'},         # Gold/Vibrant yellow
            {'label': 'Duplicate Names', 'color': 'FF6347'}, # Tomato red
            {'label': 'To be Check', 'color': 'FFD700'},   # Gold
            {'label': 'Check Ventrata', 'color': 'C27CA0'}, # Orange
            {'label': 'Changed', 'color': '259ef5'},       # Sky blue (baby blue)
            {'label': 'Will Cancel', 'color': 'FF69B4'},   # Hot pink
            {'label': 'Move', 'color': '32CD32'},          # Lime green
            {'label': 'Get Extra', 'color': 'CFE2F3'},     # Gold
            {'label': 'Private', 'color': '8E7DC2'},       # Plum (Light purple)
        ],
    },
    {
        'keywords': [
            'colosseum',
            'colosseo',
            'kolosseum',
            'colisée',
        ],
        'options': [
            {'label': 'Dash Sent', 'color': 'FFC0CB'},         # Pink
            {'label': 'Names Confirmed', 'color': '90EE90'},   # Light green
            {'label': 'Names Missing', 'color': 'FFA500'},     # Orange
            {'label': 'Canceled', 'color': 'FF0000'},          # Bright red
            {'label': 'Need New Tix', 'color': '9370DB'},      # Purple (Medium Purple)
        ],
    },
]


# Default tag options for all products (except Colosseum)
DEFAULT_TAG_OPTIONS = [
    {'label': 'Missing Name', 'color': 'FFA500'},      # Orange
    {'label': 'Done', 'color': '69A750'},              # Grass green
    {'label': 'Extra', 'color': '9FC5E7'},             # Gold/Vibrant yellow
    {'label': 'Duplicate Names', 'color': 'FF6347'},   # Tomato red
    {'label': 'To be Check', 'color': 'FFD700'},       # Gold
    {'label': 'Check Ventrata', 'color': 'C27CA0'},   # Orange
    {'label': 'Changed', 'color': '259ef5'},           # Sky blue (baby blue)
    {'label': 'Will Cancel', 'color': 'FF69B4'},       # Hot pink
    {'label': 'Move', 'color': '32CD32'},               # Lime green
    {'label': 'Get Extra', 'color': 'CFE2F3'},         # Gold
    {'label': 'Private', 'color': '8E7DC2'},           # Plum (Light purple)
]


def get_tag_options(product_code: str = "", product_tags: str = "") -> List[Dict[str, str]]:
    """
    Return tag options (label/color) for the given product info.

    Args:
        product_code: Product code string
        product_tags: Product tags string

    Returns:
        list[dict]: List of {'label': str, 'color': str} dicts
    """
    searchable_text = " ".join([
        str(product_code or "").lower(),
        str(product_tags or "").lower()
    ])

    # Check if product has "colosseo" in tags - if so, return Colosseum tags only (Tag column will be hidden)
    if 'colosseo' in searchable_text:
        for definition in TAG_DEFINITIONS:
            if 'colosseo' in definition['keywords']:
                return definition['options']

    # Check for Castle products (including ROMSAN - Castle Sant'Angelo)
    for definition in TAG_DEFINITIONS:
        if any(keyword in searchable_text for keyword in definition['keywords']):
            return definition['options']

    # Default tags for all other products (that don't have colosseo)
    return DEFAULT_TAG_OPTIONS
