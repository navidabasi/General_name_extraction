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
        ],
        'options': [
            {'label': 'Canceled', 'color': 'FF0000'},      # Red
            {'label': 'Use Cancele', 'color': 'FFC0CB'},   # Pink
            {'label': 'Waiting', 'color': 'A9A9A9'},       # Dark gray
            {'label': 'Use Waiting', 'color': 'FFBF00'},   # Amber
            {'label': 'Burned', 'color': 'BEBEBE'},        # Gray
        ],
    },
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
    
    for definition in TAG_DEFINITIONS:
        if any(keyword in searchable_text for keyword in definition['keywords']):
            return definition['options']
    
    return []


