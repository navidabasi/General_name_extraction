"""
Non-GetYourGuide Extractor.

Handles all non-GYG reseller platforms.

For non-GYG platforms, names are already structured in the Ventrata data:
- Uses "Ticket Customer First Name" and "Ticket Customer Last Name" columns
- No complex pattern matching required
- Simple validation only
"""

import pandas as pd
import logging

from .base_extractor import BaseExtractor
from config import ALL_GYG_PLATFORMS

logger = logging.getLogger(__name__)


class NonGYGExtractor(BaseExtractor):
    """
    Extractor for non-GYG reseller platforms.
    
    Names are already in structured columns, so extraction is simple.
    """
    
    def get_reseller_types(self):
        """
        Return list of non-GYG reseller names.
        
        Since this handles all non-GYG platforms, returns empty list
        (acts as catch-all for anything not in GYG lists).
        """
        return []  # Catch-all for non-GYG
    
    def extract_travelers(self, public_notes, order_ref, booking_data=None):
        """
        Extract travelers from structured Ventrata columns.
        
        For non-GYG platforms, names are in:
        - Ticket Customer First Name
        - Ticket Customer Last Name
        
        Args:
            public_notes: Public notes text (not used for non-GYG)
            order_ref: Order reference for logging
            booking_data: Required dict with booking row data
            
        Returns:
            list: List of traveler dicts
        """
        if booking_data is None:
            logger.error(f"[Non-GYG] No booking data provided for order {order_ref}")
            return []
        
        # Get name from structured columns
        first_name = booking_data.get('first_name', '')
        last_name = booking_data.get('last_name', '')
        
        # Handle None values
        if pd.isna(first_name):
            first_name = ''
        if pd.isna(last_name):
            last_name = ''
        
        first_name = str(first_name).strip()
        last_name = str(last_name).strip()
        
        # Construct full name
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        else:
            # Don't use Customer field as fallback - it's the lead traveler, not individual travelers
            # Missing names should remain empty to trigger proper error handling
            logger.warning(f"[Non-GYG] No name found for row in order {order_ref} - first_name and last_name both empty")
            full_name = ''
        
        # Clean up the name and normalize accents
        full_name = self.clean_name(full_name)
        
        if not full_name:
            logger.warning(f"[Non-GYG] Empty name for order {order_ref}")
            return []
        
        # Get unit type directly from structured columns
        unit_type_raw = booking_data.get('unit', '')
        if pd.isna(unit_type_raw):
            unit_type_raw = ''
        unit_type_str = str(unit_type_raw).strip()
        
        if not unit_type_str:
            logger.debug(f"[Non-GYG] No unit type found for '{full_name}' in order {order_ref}")
        
        # For non-GYG platforms, DOBs are typically not provided
        # We return just the name without age information but preserve unit type from Ventrata
        traveler = {
            'name': full_name,
            'dob': None,
            'age': None,
            'is_child_by_age': False,
            'is_youth_by_age': False,
            'is_adult_by_age': False,
            'unit_type': unit_type_str,
            'original_unit_type': unit_type_str
        }
        
        logger.debug(f"[Non-GYG] Extracted name '{full_name}' for order {order_ref}")
        
        # Return as single-item list (one name per row)
        return [traveler]
    
    def is_non_gyg_reseller(self, reseller):
        """
        Check if reseller is non-GYG.
        
        Args:
            reseller: Reseller name string
            
        Returns:
            bool: True if non-GYG platform
        """
        if pd.isna(reseller) or reseller is None:
            return True  # Assume non-GYG if no reseller specified
        
        reseller_str = str(reseller)
        
        # Check if it's any GYG platform
        for gyg_platform in ALL_GYG_PLATFORMS:
            if gyg_platform in reseller_str:
                return False
        
        return True

