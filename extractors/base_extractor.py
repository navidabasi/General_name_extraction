"""
Base extractor class defining the interface for all name extractors.
"""

import re
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all name/DOB extractors.
    
    Each extractor must implement:
    - extract_travelers: Extract names and DOBs from public notes
    - get_reseller_types: Return list of reseller names this extractor handles
    """
    
    @abstractmethod
    def extract_travelers(self, public_notes, order_ref, booking_data=None):
        """
        Extract traveler information from public notes.
        
        Args:
            public_notes: Public notes text from booking
            order_ref: Order reference for logging
            booking_data: Optional dict with additional booking info
            
        Returns:
            list: List of dicts with structure:
                {
                    'name': str,
                    'dob': str or None,
                    'age': float or None,
                    'is_child_by_age': bool,
                    'is_youth_by_age': bool,
                    'is_adult_by_age': bool
                }
        """
        pass
    
    @abstractmethod
    def get_reseller_types(self):
        """
        Get list of reseller types this extractor handles.
        
        Returns:
            list: List of reseller name strings
        """
        pass
    
    def clean_name(self, name):
        """
        Clean and normalize extracted name.
        
        - Strips leading/trailing whitespace
        - Normalizes multiple spaces to single space
        - Removes leading numbers, dots, dashes
        - Removes trailing date indicators
        
        Args:
            name: Raw name string
            
        Returns:
            str: Cleaned name
        """
        if not name or not isinstance(name, str):
            return ""
        
        name = name.strip()
        
        # Remove leading numbers, dots, dashes
        name = re.sub(r'^[\d\.\-\s]*', '', name)
        name = re.sub(r'^[\s\-]+', '', name)
        
        # Remove trailing text like "DOB", dashes, dots
        name = re.sub(r'\s*-\s*DOB\s*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*-\s*$', '', name)
        name = re.sub(r'\s*DOB\s*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\.\s*$', '', name)
        
        # Remove common trailing date indicators
        name = re.sub(r'\s*-\s*\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}.*$', '', name)
        
        # Remove age indicators (French: "ans", English: "years", "yrs", "yo", etc.)
        # Pattern: "- 41 ans" or "- 16 years" or "- 25 yrs" or "- 30 yo"
        name = re.sub(r'\s*-\s*\d+\s*(ans|years?|yrs?|yo|age)\s*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\(\s*\d+\s*(ans|years?|yrs?|yo|age)\s*\)\s*$', '', name, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def validate_name_structure(self, name):
        """
        Validate that a name has proper structure.
        
        Requirements:
        - At least 2 words (first and last name)
        - Only alphabetic characters (allowing hyphens, apostrophes, dots)
        - No instruction-like words
        
        Args:
            name: Name string to validate
            
        Returns:
            bool: True if valid name structure
        """
        if not name or not isinstance(name, str):
            return False
        
        # Must have at least 2 words
        words = name.split()
        if len(words) < 2:
            return False
        
        # Check for instruction words
        instruction_words = [
            'provide', 'participants', 'group', 'birth', 'date',
            'full', 'names', 'everyone', 'all', 'please', 'also'
        ]
        name_lower = name.lower()
        for word in instruction_words:
            if word in name_lower:
                return False
        
        # All words must be valid name characters
        for word in words:
            if not re.match(r"^[A-Za-zÀ-ÿĀ-žА-я\u00C0-\u017F\u1E00-\u1EFF\u0100-\u024F'\.\-]+$", word):
                return False
        
        return True
    
    def filter_instruction_lines(self, lines):
        """
        Filter out lines that appear to be instructions rather than data.
        
        Args:
            lines: List of text lines
            
        Returns:
            list: Filtered lines
        """
        filtered = []
        instruction_pattern = r'\b(?:provide|participants|group|birth|date|full|names|everyone|all|please)\b'
        
        for line in lines:
            line = line.strip()
            if line and not re.search(instruction_pattern, line, re.IGNORECASE):
                filtered.append(line)
        
        return filtered

