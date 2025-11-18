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
            # Check if there's a 'Customer' field as fallback
            customer = booking_data.get('customer', '')
            if customer and not pd.isna(customer):
                full_name = str(customer).strip()
            else:
                logger.warning(f"[Non-GYG] No name found for order {order_ref}")
                full_name = ''
        
        # Clean up the name
        full_name = full_name.strip()
        
        if not full_name:
            logger.warning(f"[Non-GYG] Empty name for order {order_ref}")
            return []
        
        # For non-GYG platforms, DOBs are typically not provided
        # We return just the name without age information
        traveler = {
            'name': full_name,
            'dob': None,
            'age': None,
            'is_child_by_age': False,
            'is_youth_by_age': False,
            'is_adult_by_age': False
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

