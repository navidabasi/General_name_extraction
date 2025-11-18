"""
GetYourGuide Standard Extractor.

Handles standard GYG platforms:
- GetYourGuide
- GetYourGuide EC
- Get your Guide T&T
- Get your Guide Giano
- Get your Guide Infinity

Uses structured format with "First Name:" and "Last Name:" labels.
"""

import re
import pandas as pd
import logging
from datetime import datetime

from .base_extractor import BaseExtractor
from config import GYG_STANDARD_PLATFORMS
from utils.age_calculator import calculate_age_on_travel_date

logger = logging.getLogger(__name__)


class GYGStandardExtractor(BaseExtractor):
    """
    Extractor for standard GetYourGuide platforms.
    
    Expects public notes format:
        First Name: John
        Last Name: Smith
        Date of Birth: 15/03/1990
        ...
        First Name: Jane
        Last Name: Doe
        Date of Birth: 1985-06-20
    """
    
    def get_reseller_types(self):
        """Return list of GYG standard reseller names."""
        return GYG_STANDARD_PLATFORMS
    
    def extract_travelers(self, public_notes, order_ref, booking_data=None):
        """
        Extract travelers from GYG standard format public notes.
        
        Args:
            public_notes: Public notes text
            order_ref: Order reference for logging
            booking_data: Optional booking data dict
            
        Returns:
            list: List of traveler dicts
        """
        if not public_notes or pd.isna(public_notes):
            logger.warning(f"[GYG Standard] No public notes for order {order_ref}")
            return []
        
        public_notes_str = str(public_notes)
        
        # Extract names and DOBs
        names = self._extract_names(public_notes_str)
        dobs = self._extract_dobs(public_notes_str)
        
        logger.info(f"[GYG Standard] Order {order_ref}: Found {len(names)} names, {len(dobs)} DOBs")
        
        if not names:
            logger.warning(f"[GYG Standard] No names extracted for order {order_ref}")
            return []
        
        # Get travel date from booking data if available
        travel_date = None
        if booking_data and 'travel_date' in booking_data:
            travel_date = booking_data['travel_date']
            if travel_date:
                logger.debug(f"[GYG Standard] Travel date for {order_ref}: {travel_date}")
            else:
                logger.warning(f"[GYG Standard] Travel date is None/empty for {order_ref}")
        
        # Build traveler list
        travelers = []
        for idx, name in enumerate(names):
            # Match DOB to name if available
            dob_str = None
            age_value = None
            is_child_by_age = False
            is_youth_by_age = False
            is_adult_by_age = False
            
            if idx < len(dobs):
                dob_str = dobs[idx]
                
                # Calculate age
                if travel_date and not pd.isna(travel_date):
                    age_value = calculate_age_on_travel_date(dob_str, travel_date)
                    if age_value is None:
                        logger.warning(f"[GYG Standard] Failed to calculate age for {name} with DOB {dob_str} and travel date {travel_date}")
                else:
                    logger.warning(f"[GYG Standard] No travel date available for {name}, cannot calculate age from DOB {dob_str}")
                    age_value = None
                
                # Categorize by age
                if age_value is not None:
                    is_child_by_age = age_value < 18
                    is_youth_by_age = 18 <= age_value < 25
                    is_adult_by_age = age_value >= 25
            
            travelers.append({
                'name': name,
                'dob': dob_str,
                'age': age_value,
                'is_child_by_age': is_child_by_age,
                'is_youth_by_age': is_youth_by_age,
                'is_adult_by_age': is_adult_by_age
            })
        
        logger.info(f"[GYG Standard] Extracted {len(travelers)} travelers for order {order_ref}")
        return travelers
    
    def _extract_names(self, public_notes):
        """
        Extract names from GYG standard format.
        
        Pattern: "First Name: John\nLast Name: Smith"
        
        Args:
            public_notes: Public notes text
            
        Returns:
            list: List of full names
        """
        name_pattern = r"(?:First Name:|First name:)\s*([^\n:]+)\s*(?:Last Name:|Last name:)\s*([^\n:]+)"
        name_matches = re.findall(name_pattern, public_notes, re.IGNORECASE)
        
        names = []
        for first, last in name_matches:
            full_name = f"{first.strip()} {last.strip()}"
            names.append(full_name)
        
        return names
    
    def _extract_dobs(self, public_notes):
        """
        Extract dates of birth from GYG public notes.
        
        Supports two formats:
        - DD/MM/YYYY format: "Date of Birth: 15/03/1990"
        - YYYY-MM-DD format: "Date of Birth: 1990-03-15"
        
        Args:
            public_notes: Public notes text
            
        Returns:
            list: List of DOB strings in order of appearance
        """
        # Pattern 1: DD/MM/YYYY format
        dob_pattern_slash = r"Date of Birth:\s*(\d{2}/\d{2}/\d{4})"
        slash_dobs = re.findall(dob_pattern_slash, public_notes)
        
        # Pattern 2: YYYY-MM-DD format
        dob_pattern_dash = r"Date of Birth:\s*(\d{4}-\d{2}-\d{2})"
        dash_dobs = re.findall(dob_pattern_dash, public_notes)
        
        # Combine maintaining order of appearance
        all_dobs = slash_dobs + dash_dobs
        
        return all_dobs

