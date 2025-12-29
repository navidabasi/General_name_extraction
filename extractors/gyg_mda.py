"""
GetYourGuide MDA Extractor.

Handles Get your Guide MDA platform with 24 different regex patterns
for extracting traveler names and dates of birth from various formats.

Patterns are tried in priority order (most structured first, least structured last).
"""

import re
import pandas as pd
import logging
from datetime import datetime
import sys
import os

# Handle both relative import (when used as module) and absolute import (when run directly)
try:
    from .base_extractor import BaseExtractor
except ImportError:
    # If relative import fails, try absolute import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractors.base_extractor import BaseExtractor

from config import GYG_MDA_PLATFORM

logger = logging.getLogger(__name__)


class GYGMDAExtractor(BaseExtractor):


    PATTERN_TRAVELER = re.compile(r'Traveler \d+:', re.IGNORECASE)
    PATTERN_INSTRUCTION_WORDS = re.compile(r'\b(?:provide|participants|group|birth|date|full|names|everyone|all|please)\b', re.IGNORECASE)
    PATTERN_DDMMYYYY_DOT = re.compile(r'\d{1,2}\.\d{1,2}\.\d{4}')
    PATTERN_NAME_DATE_DOT = re.compile(r'[A-Za-zÀ-ÿ\s\-\'\.]+\s+\d{1,2}\.\d{1,2}\.\d{4}')
    PATTERN_DDMMYYYY_DOT_END = re.compile(r'\d{1,2}\.\d{1,2}\.\d{4}\.')
    PATTERN_NAME_DATE_SLASH = re.compile(r'[A-Za-zÀ-ÿ\s\-\'\.]+\s+\d{1,2}/\d{1,2}/\d{4}\.?')
    PATTERN_NAME_PAREN_DATE = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s*\((\d{1,2}/\d{1,2}/\d{2,4})\)')
    PATTERN_NAME_PAREN_YYYYMMDD = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s*\((\d{4}\.\d{1,2}\.\d{1,2}\.?)\)')
    PATTERN_NAME_ADULT_CHILD_DATE = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s*\((adult|child)\)\s*(\d{1,2}-\d{1,2}-\d{4})', re.IGNORECASE)
    PATTERN_NAME_DDMMMYYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s*\((\d{1,2}[a-zA-Z]{3}\d{4})\)')
    PATTERN_NAME_YYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s*\((\d{4})\)')
    PATTERN_NAME_DDMMYYYY_DOT_LINE = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+?)\s+(\d{1,2}\.\d{1,2}\.\d{4})\.?')
    PATTERN_NAME_COMMA_DDMMYYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+),\s*(\d{1,2}\.\d{1,2}\.\d{4}\.?)')
    PATTERN_NAME_SLASH_DDMMYYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)/\s*(\d{1,2}\.\d{1,2}\.\d{4})')
    PATTERN_NAME_MONTH_DAY_YEAR = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})')
    PATTERN_NAME_D_M_YYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')
    PATTERN_NAME_DD_MONTH_YYYY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})')
    PATTERN_NAME_DD_MM_YYYY_DASH = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+)\s+(\d{1,2}-\d{1,2}-\d{4})')
    PATTERN_NAME_DOB_EXTENDED = re.compile(r'([A-Za-zÀ-ÿĀ-žА-я\u00C0-\u017F\u1E00-\u1EFF\u0100-\u024F\s\-\'.]{3,50})\s*-\s*(?:DOB\s*)?(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{1,2}[/\.]\d{1,2}[/\.]\d{4})', re.IGNORECASE)
    PATTERN_NAME_PAREN_DATE_EXTENDED = re.compile(r'-?\s*([A-Za-zÀ-ÿĀ-žА-я\u00C0-\u017F\u1E00-\u1EFF\u0100-\u024F\s\-\'.]{3,50})\s*\((\d{1,2}[/\.]\d{1,2}[/\.]\d{4})\)\s*,?', re.IGNORECASE)
    PATTERN_NAME_WRITTEN_DATE = re.compile(r'([A-Za-zÀ-ÿĀ-žА-я\u00C0-\u017F\u1E00-\u1EFF\u0100-\u024F\s\-\'.]{3,50})\s*-\s*([a-zA-Z]+\s+\d{1,2},\s+\d{4})', re.IGNORECASE)
    PATTERN_FRENCH_AGE = re.compile(r'-\s*([A-Za-zÀ-ÿ\s\-\'\.]+)\s*:\s*(\d+)\s*ans?', re.IGNORECASE)
    PATTERN_ORDINAL_DATE = re.compile(r'\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]+\s+\d{4}')
    PATTERN_VALID_NAME_WORD = re.compile(r"^[A-Za-zÀ-ÿ'\.\-]+$")
    PATTERN_FLOOR = re.compile(r'^\d+(?:st|nd|rd|th)?\s+floor', re.IGNORECASE)
    PATTERN_RMZ = re.compile(r'^RMZ', re.IGNORECASE)
    PATTERN_NAME_DATE_MULTILINE = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+?)(?:\s+(\d{1,2}/\d{1,2}/\d{2,4}))?\s*(?=\n|$)', re.MULTILINE)
    PATTERN_FIRST_NAME = re.compile(r'First Name:\s*([^\n:]+)', re.IGNORECASE)
    PATTERN_LAST_NAME = re.compile(r'Last Name:\s*([^\n:]+)', re.IGNORECASE)
    PATTERN_DOB_ISO = re.compile(r'Date of Birth:\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE)   
    PATTERN_ORDINAL_ENTRY = re.compile(r'^(.+?)\s+(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]+\s+\d{4})$')
    PATTERN_DDMMMYYYY_MATCH = re.compile(r'^(\d{1,2})([a-zA-Z]{3})(\d{4})$')
    PATTERN_AND_SPLIT = re.compile(r'\s+and\s+', re.IGNORECASE)
    PATTERN_INSTRUCTION_WORDS_EXTENDED = re.compile(r'\b(?:provide|participants|group|birth|date|full|names|everyone|all|please|also|and)\b', re.IGNORECASE)
    PATTERN_PATTERN20_ENTRY = re.compile(r'^(.+?)\s+(\d{1,2}\.\d{1,2}\.\d{4})\.?$')
    PATTERN_PATTERN21_ENTRY = re.compile(r'([A-Za-zÀ-ÿ\s\-\'\.]+?)\s+(\d{1,2}/\d{1,2}/\d{4})\.?')
    PATTERN_PATTERN22_ENTRY = re.compile(r'^(.+?)\s+(\d{1,2}\.\d{1,2}\.\d{4})\.?$')
    PATTERN_ORDINAL_CLEAN = re.compile(r'(\d+)(?:st|nd|rd|th)')
    PATTERN_TRAILING_COMMA_SPACE = re.compile(r'[,\s]+$')

    """
    Extractor for GetYourGuide MDA platform.
    
    Tries 24 different patterns in priority order to extract
    traveler information from unstructured public notes.
    """
    
    def get_reseller_types(self):
        """Return list of GYG MDA reseller name."""
        return [GYG_MDA_PLATFORM]
    
    def extract_travelers(self, public_notes, order_ref, booking_data=None):
        """
        Extract travelers using pattern matching (24 patterns in priority order).
        
        Args:
            public_notes: Public notes text
            order_ref: Order reference for logging
            booking_data: Optional booking data dict
            
        Returns:
            list: List of traveler dicts
        """
        if not public_notes or pd.isna(public_notes):
            logger.warning(f"[GYG MDA] No public notes for order {order_ref}")
            return []
        
        travelers = []
        current_date = datetime.now()
        
        # Cache fast string checks once at the start (avoid repeated 'in' operations)
        public_notes_lower = public_notes.lower()
        has_traveler = 'traveler' in public_notes_lower
        has_parentheses = '(' in public_notes and ')' in public_notes
        has_dots = '.' in public_notes
        has_slashes = '/' in public_notes
        has_dashes = '-' in public_notes
        has_commas = ',' in public_notes
        
        try:
            # Try patterns in priority order (most specific first)
            
            # Pattern 1: Structured format with "Traveler X:", "First Name:", etc.
            # Fast string check before regex
            if has_traveler:
                if self.PATTERN_TRAVELER.search(public_notes):
                    logger.debug(f"[GYG MDA] Trying Pattern 1 for {order_ref}")
                    travelers = self._extract_pattern1(public_notes, current_date)
                    if travelers:
                        return travelers
            
            # Pattern 20: Comma-separated entries with DD.MM.YYYY dates (single line)
            # Fast string check - skip entire pattern if no commas or dots (use cached values)
            if has_commas and has_dots:
                lines = public_notes.split('\n')
                for line in lines:
                    line = line.strip()
                    # Fast string checks for this specific line
                    if (line and 
                        ',' in line and  # Fast check - line has comma
                        '.' in line):  # Fast check - line has dots
                        if (not self.PATTERN_INSTRUCTION_WORDS.search(line) and
                            self.PATTERN_DDMMYYYY_DOT.search(line) and
                            len(self.PATTERN_NAME_DATE_DOT.findall(line)) >= 2):
                            logger.debug(f"[GYG MDA] Trying Pattern 20 for {order_ref}")
                            travelers = self._extract_pattern20(line, current_date)
                            if travelers:
                                return travelers
            
            # Pattern 21: Space-separated entries with DD/MM/YYYY dates (single line)
            # Fast string check - skip entire pattern if no slashes (use cached value)
            if has_slashes:
                for line in lines:
                    line = line.strip()
                    # Fast string check for this specific line
                    if (line and '/' in line):  # Fast check - line has slash
                        if (not self.PATTERN_INSTRUCTION_WORDS.search(line) and
                            self.PATTERN_NAME_DATE_SLASH.findall(line) and
                            len(self.PATTERN_NAME_DATE_SLASH.findall(line)) >= 2):
                            logger.debug(f"[GYG MDA] Trying Pattern 21 for {order_ref}")
                            travelers = self._extract_pattern21(line, current_date)
                            if travelers:
                                return travelers
            
            # Pattern 22: Mixed comma and period format
            # Fast string check - skip entire pattern if no commas or dots (use cached values)
            if has_commas and has_dots:
                for line in lines:
                    line = line.strip()
                    # Fast string checks for this specific line
                    if (line and 
                        ',' in line and  # Fast check - line has comma
                        '.' in line):  # Fast check - line has dots
                        if (not self.PATTERN_INSTRUCTION_WORDS.search(line) and
                            self.PATTERN_DDMMYYYY_DOT_END.search(line)):
                            logger.debug(f"[GYG MDA] Trying Pattern 22 for {order_ref}")
                            travelers = self._extract_pattern22(line, current_date)
                            if travelers:
                                return travelers
            
            # Pattern 2: Name (DD/MM/YYYY) or Name (DD/MM/YY) format
            # Fast string check - pattern requires parentheses (use cached value)
            if has_parentheses:
                pattern2_matches = []
                for line in lines:
                    line = line.strip()
                    # Fast check for parentheses in this line
                    if (line and 
                        '(' in line and ')' in line and  # Fast check
                        not self.PATTERN_INSTRUCTION_WORDS.search(line)):
                        matches = self.PATTERN_NAME_PAREN_DATE.findall(line)
                        if matches:
                            pattern2_matches.extend(matches)
            else:
                pattern2_matches = []
            
            if pattern2_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 2 for {order_ref}")
                travelers = self._extract_pattern2(pattern2_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 11: Dot-separated dates in parentheses (Name (YYYY.MM.DD))
            # Fast string check - pattern requires parentheses and dots (use cached values)
            if has_parentheses and has_dots:
                pattern11_travelers = []
                for line in lines:
                    line = line.strip()
                    # Fast check for parentheses and dots in this line
                    if (line and 
                        '(' in line and ')' in line and '.' in line and  # Fast checks
                        not self.PATTERN_INSTRUCTION_WORDS.search(line)):
                        matches = self.PATTERN_NAME_PAREN_YYYYMMDD.findall(line)
                        if matches:
                            for match in matches:
                                name = match[0].strip()
                                if (len(name.split()) >= 2 and 
                                    not self.PATTERN_INSTRUCTION_WORDS.search(name)):
                                    pattern11_travelers.append(match)
            else:
                pattern11_travelers = []
            
            if pattern11_travelers:
                logger.debug(f"[GYG MDA] Trying Pattern 11 for {order_ref}")
                travelers = self._extract_pattern11(pattern11_travelers, current_date)
                if travelers:
                    return travelers
            
            # Pattern 17: Name (adult/child) DD-MM-YYYY format
            # Fast string check - requires parentheses, "adult"/"child", and dashes (use cached values)
            if has_parentheses and has_dashes:
                pattern17_matches = self.PATTERN_NAME_ADULT_CHILD_DATE.findall(public_notes)
            else:
                pattern17_matches = []
            if pattern17_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 17 for {order_ref}")
                travelers = self._extract_pattern17(pattern17_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 18: Name (DDmmmYYYY) format
            # Fast string check - requires parentheses (use cached value)
            if has_parentheses:
                pattern18_matches = self.PATTERN_NAME_DDMMMYYYY.findall(public_notes)
            else:
                pattern18_matches = []
            if pattern18_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 18 for {order_ref}")
                travelers = self._extract_pattern18(pattern18_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 16: Name (YYYY) format (birth year only)
            # Fast string check - requires parentheses (use cached value)
            if has_parentheses:
                pattern16_matches = self.PATTERN_NAME_YYYY.findall(public_notes)
            else:
                pattern16_matches = []
            if pattern16_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 16 for {order_ref}")
                travelers = self._extract_pattern16(pattern16_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 12: Name DD.MM.YYYY format
            # Fast string check - requires dots for dates (use cached value)
            pattern12_matches = []
            if has_dots:
                for line in lines:
                    line = line.strip()
                    # Fast check for dots in this line
                    if (line and 
                        '.' in line and  # Fast check
                        not self.PATTERN_INSTRUCTION_WORDS.search(line)):
                        matches = self.PATTERN_NAME_DDMMYYYY_DOT_LINE.findall(line)
                        if matches:
                            pattern12_matches.extend(matches)
            
            if pattern12_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 12 for {order_ref}")
                travelers = self._extract_pattern12(pattern12_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 13: Name, DD.MM.YYYY format
            # Fast string check - requires comma and dots (use cached values)
            pattern13_matches = []
            if has_commas and has_dots:
                for line in lines:
                    line = line.strip()
                    # Fast checks for comma and dots in this line
                    if (line and 
                        ',' in line and '.' in line and  # Fast checks
                        not self.PATTERN_INSTRUCTION_WORDS.search(line)):
                        matches = self.PATTERN_NAME_COMMA_DDMMYYYY.findall(line)
                        if matches:
                            pattern13_matches.extend(matches)
            
            if pattern13_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 13 for {order_ref}")
                travelers = self._extract_pattern13(pattern13_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 14: Name/ DD.MM.YYYY format
            # Fast string check - requires slash and dots (use cached values)
            if has_slashes and has_dots:
                pattern14_matches = self.PATTERN_NAME_SLASH_DDMMYYYY.findall(public_notes)
            else:
                pattern14_matches = []
            if pattern14_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 14 for {order_ref}")
                travelers = self._extract_pattern14(pattern14_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 15: Name Month DD, YYYY format
            # Fast string check - requires month names and commas
            if has_commas:
                pattern15_matches = self.PATTERN_NAME_MONTH_DAY_YEAR.findall(public_notes)
            else:
                pattern15_matches = []
            if pattern15_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 15 for {order_ref}")
                travelers = self._extract_pattern15(pattern15_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 19: Name D. M. YYYY format
            # Fast string check - requires dots (use cached value)
            if has_dots:
                pattern19_matches = self.PATTERN_NAME_D_M_YYYY.findall(public_notes)
            else:
                pattern19_matches = []
            if pattern19_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 19 for {order_ref}")
                travelers = self._extract_pattern19(pattern19_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 6: Name DD Month YYYY format
            # Fast string check - requires month names (no specific char check, but month names are required)
            pattern6_matches = self.PATTERN_NAME_DD_MONTH_YYYY.findall(public_notes)
            if pattern6_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 6 for {order_ref}")
                travelers = self._extract_pattern6(pattern6_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 7: Name DD-MM-YYYY format (with dashes)
            # Fast string check - requires dashes (use cached value)
            if has_dashes:
                pattern7_matches = self.PATTERN_NAME_DD_MM_YYYY_DASH.findall(public_notes)
            else:
                pattern7_matches = []
            if pattern7_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 7 for {order_ref}")
                travelers = self._extract_pattern7(pattern7_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 3: Name - DDth Month YYYY format or Name - DD.MM.YYYY format
            # Fast string check - requires dashes (use cached value)
            pattern3_matches = []
            if has_dashes:
                for line in public_notes.split('\n'):
                    line = line.strip()
                    # Fast check for dash in this line
                    if line and '-' in line:
                        if self.PATTERN_INSTRUCTION_WORDS.search(line):
                            continue
                        matches = self.PATTERN_NAME_DOB_EXTENDED.findall(line)
                        pattern3_matches.extend(matches)
            
            if pattern3_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 3 for {order_ref}")
                travelers = self._extract_pattern3(pattern3_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 23: Parentheses format - Name (DD/MM/YYYY), or - Name (DD/MM/YYYY),
            # Fast string check - requires parentheses and slashes (use cached values)
            pattern23_matches = []
            if has_parentheses and has_slashes:
                for line in public_notes.split('\n'):
                    line = line.strip()
                    # Fast checks for parentheses and slash in this line
                    if line and '(' in line and ')' in line and '/' in line:
                        if self.PATTERN_INSTRUCTION_WORDS.search(line):
                            continue
                        matches = self.PATTERN_NAME_PAREN_DATE_EXTENDED.findall(line)
                        pattern23_matches.extend(matches)
            
            if pattern23_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 23 for {order_ref}")
                travelers = self._extract_pattern23(pattern23_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 24: Written dates format - Name - month day, year
            # Fast string check - requires dashes and commas (use cached values)
            pattern24_matches = []
            if has_dashes and has_commas:
                for line in public_notes.split('\n'):
                    line = line.strip()
                    # Fast checks for dash and comma in this line
                    if line and '-' in line and ',' in line:
                        if self.PATTERN_INSTRUCTION_WORDS.search(line):
                            continue
                        matches = self.PATTERN_NAME_WRITTEN_DATE.findall(line)
                        pattern24_matches.extend(matches)
            
            if pattern24_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 24 for {order_ref}")
                travelers = self._extract_pattern24(pattern24_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 10: French age format (- NAME : XX ans)
            # Fast string check - requires dashes and "ans" keyword
            if has_dashes and ('ans' in public_notes_lower or 'an' in public_notes_lower):
                pattern10_matches = self.PATTERN_FRENCH_AGE.findall(public_notes)
            else:
                pattern10_matches = []
            if pattern10_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 10 for {order_ref}")
                travelers = self._extract_pattern10(pattern10_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 8: Comma-separated names without dates
            # Fast string check - requires commas or "and" keyword (use cached value)
            if has_commas or ' and ' in public_notes_lower:
                for line in lines:
                    line = line.strip()
                    line_lower = line.lower()
                    # Fast checks for comma or "and" in this line
                    if (line and 
                        (',' in line or ' and ' in line_lower) and
                        not self.PATTERN_INSTRUCTION_WORDS.search(line) and
                        (',' in line and len(line.split(',')) >= 2) or (' and ' in line_lower and len(line.split(' and ')) >= 2)):
                        
                        # Check if this is Pattern 9 (comma-separated with ordinal dates)
                        if self.PATTERN_ORDINAL_DATE.search(line):
                            logger.debug(f"[GYG MDA] Trying Pattern 9 for {order_ref}")
                            travelers = self._extract_pattern9(line, current_date)
                            if travelers:
                                return travelers
                        else:
                            # Pattern 8 logic for names without dates
                            if ',' in line:
                                potential_names = [self.clean_name(name.strip()) for name in line.split(',')]
                            else:
                                potential_names = [name.strip() for name in self.PATTERN_AND_SPLIT.split(line)]
                            
                            valid_names = []
                            for name in potential_names:
                                if (name and 
                                    len(name.split()) >= 2 and
                                    not self.PATTERN_INSTRUCTION_WORDS.search(name) and
                                    all(self.PATTERN_VALID_NAME_WORD.match(word) for word in name.split())):
                                    valid_names.append(name)
                            
                            if len(valid_names) >= 2:
                                logger.debug(f"[GYG MDA] Trying Pattern 8 for {order_ref}")
                                travelers = self._extract_pattern8(valid_names)
                                if travelers:
                                    return travelers
            
            # Pattern 4: Name DD/MM/YY or Name MM/DD/YY format (mixed)
            # Fast string check - requires slashes (use cached value)
            if has_slashes:
                pattern4_matches = self.PATTERN_NAME_DATE_MULTILINE.findall(public_notes)
            else:
                pattern4_matches = []
            if pattern4_matches:
                logger.debug(f"[GYG MDA] Trying Pattern 4 for {order_ref}")
                travelers = self._extract_pattern4(pattern4_matches, current_date)
                if travelers:
                    return travelers
            
            # Pattern 5: Just names without dates (LAST RESORT)
            name_lines = []
            for line in lines:
                line = line.strip()
                if (line and 
                    not self.PATTERN_INSTRUCTION_WORDS_EXTENDED.search(line) and
                    not self.PATTERN_FLOOR.match(line) and
                    not self.PATTERN_RMZ.match(line) and
                    ',' not in line and '.' not in line and '/' not in line and
                    '-' not in line and '(' not in line and
                    len(line.split()) >= 2 and len(line.split()) <= 4 and
                    all(self.PATTERN_VALID_NAME_WORD.match(word) for word in line.split()) and
                    not any(char.isdigit() for char in line)):
                    name_lines.append(line)
            
            if name_lines and len(name_lines) >= 1:
                logger.debug(f"[GYG MDA] Trying Pattern 5 (names only) for {order_ref}")
                travelers = self._extract_pattern5(name_lines)
                if travelers:
                    return travelers
            
            logger.warning(f"[GYG MDA] No recognized pattern found for order {order_ref}")
            return []
            
        except Exception as e:
            logger.error(f"[GYG MDA] Error extracting travelers for {order_ref}: {str(e)}")
            return []
    
    # ============================
    # PATTERN EXTRACTION METHODS
    # ============================
    
    def _extract_pattern1(self, public_notes, current_date):
        """Extract Pattern 1: Structured format with Traveler X:, First Name:, Last Name:, Date of Birth:"""
        travelers = []
        try:
            traveler_sections = self.PATTERN_TRAVELER.split(public_notes)[1:]
            
            for section in traveler_sections:
                first_name_match = self.PATTERN_FIRST_NAME.search(section)
                last_name_match = self.PATTERN_LAST_NAME.search(section)
                dob_match = self.PATTERN_DOB_ISO.search(section)
                
                if first_name_match and last_name_match:
                    first_name = first_name_match.group(1).strip()
                    last_name = last_name_match.group(1).strip()
                    full_name = f"{first_name} {last_name}"
                    
                    dob_str = None
                    age_value = None
                    is_child_by_age = False
                    is_youth_by_age = False
                    is_adult_by_age = False
                    
                    if dob_match:
                        dob_str = dob_match.group(1)
                        try:
                            dob_date = pd.to_datetime(dob_str, format='%Y-%m-%d')
                            age_days = (current_date - dob_date).days
                            age_value = float(age_days) / 365.25
                            is_child_by_age = age_value < 18
                            is_youth_by_age = 18 <= age_value < 25
                            is_adult_by_age = age_value >= 25
                        except Exception as e:
                            logger.warning(f"Error calculating age for {full_name}: {e}")
                    
                    travelers.append({
                        'name': full_name,
                        'dob': dob_str,
                        'age': age_value,
                        'is_child_by_age': is_child_by_age,
                        'is_youth_by_age': is_youth_by_age,
                        'is_adult_by_age': is_adult_by_age
                    })
        except Exception as e:
            logger.error(f"Error in pattern 1 extraction: {e}")
        
        return travelers
    
    def _calculate_age_and_flags(self, dob_str, current_date, date_format='%d/%m/%Y'):
        """Helper to calculate age and set age category flags."""
        try:
            dob_date = pd.to_datetime(dob_str, format=date_format)
            age_days = (current_date - dob_date).days
            age_value = float(age_days) / 365.25
            return {
                'age': age_value,
                'is_child_by_age': age_value < 18,
                'is_youth_by_age': 18 <= age_value <= 25,
                'is_adult_by_age': age_value > 25
            }
        except Exception:
            return {
                'age': None,
                'is_child_by_age': False,
                'is_youth_by_age': False,
                'is_adult_by_age': False
            }
    
    def _extract_pattern2(self, matches, current_date):
        """Extract Pattern 2: Name (DD/MM/YYYY) format"""
        travelers = []
        for name, dob_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            if dob_str:
                # Handle 2-digit years
                if len(dob_str.split('/')[-1]) == 2:
                    year = int(dob_str.split('/')[-1])
                    dob_str_full = dob_str[:-2] + ('19' if year > 50 else '20') + dob_str[-2:]
                else:
                    dob_str_full = dob_str
                
                try:
                    dob_date = pd.to_datetime(dob_str_full, format='%d/%m/%Y')
                    formatted_dob = dob_date.strftime('%d/%m/%Y')
                    age_info = self._calculate_age_and_flags(dob_str_full, current_date)
                except Exception as e:
                    logger.warning(f"Error parsing DOB {dob_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern3(self, matches, current_date):
        """Extract Pattern 3: Name - DDth Month YYYY or Name - DD.MM.YYYY format"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                if self.PATTERN_DDMMYYYY_DOT.match(date_str):
                    dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                    formatted_dob = dob_date.strftime('%d/%m/%Y')
                else:
                    clean_date = self.PATTERN_ORDINAL_CLEAN.sub(r'\1', date_str)
                    dob_date = pd.to_datetime(clean_date, format='%d %B %Y')
                    formatted_dob = dob_date.strftime('%d/%m/%Y')
                
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern4(self, matches, current_date):
        """Extract Pattern 4: Mixed format with some names having dates and some not"""
        travelers = []
        for name, dob_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            if dob_str and dob_str.strip():
                dob_str = dob_str.strip()
                # Handle 2-digit years
                if len(dob_str.split('/')[-1]) == 2:
                    year = int(dob_str.split('/')[-1])
                    dob_str = dob_str[:-2] + ('19' if year > 50 else '20') + dob_str[-2:]
                
                # Try both formats
                for fmt in ['%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        dob_date = pd.to_datetime(dob_str, format=fmt)
                        formatted_dob = dob_date.strftime('%d/%m/%Y')
                        age_info = self._calculate_age_and_flags(formatted_dob, current_date)
                        break
                    except:
                        continue
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern5(self, name_lines):
        """Extract Pattern 5: Just names without dates"""
        travelers = []
        for name in name_lines:
            name = self.clean_name(name)
            if self.validate_name_structure(name):
                travelers.append({
                    'name': name,
                    'dob': None,
                    'age': None,
                    'is_child_by_age': False,
                    'is_youth_by_age': False,
                    'is_adult_by_age': False
                })
        return travelers
    
    def _extract_pattern6(self, matches, current_date):
        """Extract Pattern 6: Name DD Month YYYY format"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                dob_date = pd.to_datetime(date_str, format='%d %B %Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern7(self, matches, current_date):
        """Extract Pattern 7: Name DD-MM-YYYY format (with dashes)"""
        travelers = []
        for name, date_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                dob_date = pd.to_datetime(date_str, format='%d-%m-%Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern8(self, names):
        """Extract Pattern 8: Comma-separated names without dates"""
        travelers = []
        for name in names:
            name = self.clean_name(name)
            if self.validate_name_structure(name):
                travelers.append({
                    'name': name,
                    'dob': None,
                    'age': None,
                    'is_child_by_age': False,
                    'is_youth_by_age': False,
                    'is_adult_by_age': False
                })
        return travelers
    
    def _extract_pattern9(self, line, current_date):
        """Extract Pattern 9: Comma-separated names with ordinal dates"""
        travelers = []
        entries = [entry.strip() for entry in line.split(',')]
        
        for entry in entries:
            if not entry:
                continue
            
            match = self.PATTERN_ORDINAL_ENTRY.search(entry.strip())
            
            if match:
                name = match.group(1).strip()
                date_str = match.group(2).strip()
                
                if (name and len(name.split()) >= 2 and
                    all(self.PATTERN_VALID_NAME_WORD.match(word) for word in name.split())):
                    
                    formatted_dob = None
                    age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
                    
                    try:
                        clean_date = self.PATTERN_ORDINAL_CLEAN.sub(r'\1', date_str)
                        dob_date = pd.to_datetime(clean_date, format='%d %B %Y')
                        formatted_dob = dob_date.strftime('%d/%m/%Y')
                        age_info = self._calculate_age_and_flags(formatted_dob, current_date)
                    except Exception as e:
                        logger.warning(f"Error parsing date {date_str}: {e}")
                    
                    travelers.append({
                        'name': name,
                        'dob': formatted_dob,
                        **age_info
                    })
        
        return travelers
    
    def _extract_pattern10(self, matches, current_date):
        """Extract Pattern 10: French age format (- NAME : XX ans)"""
        travelers = []
        for name, age_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            age_value = None
            is_child_by_age = False
            is_youth_by_age = False
            is_adult_by_age = False
            
            try:
                age_value = float(age_str)
                is_child_by_age = age_value < 18
                is_youth_by_age = 18 <= age_value < 25
                is_adult_by_age = age_value >= 25
            except Exception as e:
                logger.warning(f"Error parsing age {age_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': None,
                'age': age_value,
                'is_child_by_age': is_child_by_age,
                'is_youth_by_age': is_youth_by_age,
                'is_adult_by_age': is_adult_by_age
            })
        
        return travelers
    
    def _extract_pattern11(self, matches, current_date):
        """Extract Pattern 11: Dot-separated dates in parentheses (Name (YYYY.MM.DD))"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                clean_date = date_str.rstrip('.')
                date_parts = clean_date.split('.')
                if len(date_parts) == 3:
                    year, month, day = date_parts
                    formatted_dob = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern12(self, matches, current_date):
        """Extract Pattern 12: Name DD.MM.YYYY format"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern13(self, matches, current_date):
        """Extract Pattern 13: Name, DD.MM.YYYY format"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                clean_date = date_str.rstrip('.')
                dob_date = pd.to_datetime(clean_date, format='%d.%m.%Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern14(self, matches, current_date):
        """Extract Pattern 14: Name/ DD.MM.YYYY format"""
        travelers = []
        for name, date_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern15(self, matches, current_date):
        """Extract Pattern 15: Name Month DD, YYYY format"""
        travelers = []
        for name, month, day, year in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                date_str = f"{day} {month} {year}"
                dob_date = pd.to_datetime(date_str, format='%d %B %Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {month} {day}, {year}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern16(self, matches, current_date):
        """Extract Pattern 16: Name (YYYY) format (birth year only)"""
        travelers = []
        for name, year_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            age_value = None
            is_child_by_age = False
            is_youth_by_age = False
            is_adult_by_age = False
            
            try:
                birth_year = int(year_str)
                current_year = current_date.year
                age_value = float(current_year - birth_year)
                is_child_by_age = age_value < 18
                is_youth_by_age = 18 <= age_value < 25
                is_adult_by_age = age_value >= 25
            except Exception as e:
                logger.warning(f"Error calculating age from year {year_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': None,
                'age': age_value,
                'is_child_by_age': is_child_by_age,
                'is_youth_by_age': is_youth_by_age,
                'is_adult_by_age': is_adult_by_age
            })
        
        return travelers
    
    def _extract_pattern17(self, matches, current_date):
        """Extract Pattern 17: Name (adult/child) DD-MM-YYYY format"""
        travelers = []
        for name, age_type, date_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            is_child_by_age = age_type.lower() == 'child'
            formatted_dob = None
            age_value = None
            
            try:
                dob_date = pd.to_datetime(date_str, format='%d-%m-%Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_days = (current_date - dob_date).days
                age_value = float(age_days) / 365.25
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                'age': age_value,
                'is_child_by_age': is_child_by_age,
                'is_youth_by_age': False if is_child_by_age else (18 <= (age_value or 0) <= 25),
                'is_adult_by_age': not is_child_by_age and (age_value or 0) > 25
            })
        
        return travelers
    
    def _extract_pattern18(self, matches, current_date):
        """Extract Pattern 18: Name (DDmmmYYYY) format"""
        travelers = []
        month_map = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        for name, date_str in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                day_match = self.PATTERN_DDMMMYYYY_MATCH.match(date_str)
                if day_match:
                    day, month_abbr, year = day_match.groups()
                    month_num = month_map.get(month_abbr.lower())
                    
                    if month_num:
                        formatted_date_str = f"{day.zfill(2)}/{month_num}/{year}"
                        age_info = self._calculate_age_and_flags(formatted_date_str, current_date)
                        formatted_dob = formatted_date_str
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern19(self, matches, current_date):
        """Extract Pattern 19: Name D. M. YYYY format"""
        travelers = []
        for name, day, month, year in matches:
            name = name.strip()
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                formatted_dob = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {day}.{month}.{year}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern20(self, line, current_date):
        """Extract Pattern 20: Comma-separated entries with DD.MM.YYYY dates (single line)"""
        travelers = []
        entries = [entry.strip() for entry in line.split(',')]
        
        for entry in entries:
            if not entry:
                continue
            
            match = self.PATTERN_PATTERN20_ENTRY.search(entry.strip())
            
            if match:
                name = match.group(1).strip()
                date_str = match.group(2).strip()
                
                if (name and len(name.split()) >= 2 and
                    all(self.PATTERN_VALID_NAME_WORD.match(word) for word in name.split())):
                    
                    formatted_dob = None
                    age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
                    
                    try:
                        dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                        formatted_dob = dob_date.strftime('%d/%m/%Y')
                        age_info = self._calculate_age_and_flags(formatted_dob, current_date)
                    except Exception as e:
                        logger.warning(f"Error parsing date {date_str}: {e}")
                    
                    travelers.append({
                        'name': name,
                        'dob': formatted_dob,
                        **age_info
                    })
        
        return travelers
    
    def _extract_pattern21(self, line, current_date):
        """Extract Pattern 21: Space-separated entries with DD/MM/YYYY dates (single line)"""
        travelers = []
        matches = self.PATTERN_PATTERN21_ENTRY.findall(line)
        
        for name, date_str in matches:
            name = self.PATTERN_TRAILING_COMMA_SPACE.sub('', name.strip())
            
            if (name and len(name.split()) >= 2 and
                all(self.PATTERN_VALID_NAME_WORD.match(word) for word in name.split())):
                
                formatted_dob = None
                age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
                
                # Try both formats
                for fmt in ['%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        dob_date = pd.to_datetime(date_str, format=fmt)
                        formatted_dob = dob_date.strftime('%d/%m/%Y')
                        age_info = self._calculate_age_and_flags(formatted_dob, current_date)
                        break
                    except:
                        continue
                
                travelers.append({
                    'name': name,
                    'dob': formatted_dob,
                    **age_info
                })
        
        return travelers
    
    def _extract_pattern22(self, line, current_date):
        """Extract Pattern 22: Mixed comma and period format"""
        travelers = []
        
        if ',' in line:
            entries = [entry.strip() for entry in line.split(',')]
            for entry in entries:
                if not entry:
                    continue
                
                match = self.PATTERN_PATTERN22_ENTRY.search(entry.strip())
                
                if match:
                    name = match.group(1).strip()
                    date_str = match.group(2).strip()
                    
                    if (name and len(name.split()) >= 2 and
                        all(self.PATTERN_VALID_NAME_WORD.match(word) for word in name.split())):
                        
                        formatted_dob = None
                        age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
                        
                        try:
                            dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                            formatted_dob = dob_date.strftime('%d/%m/%Y')
                            age_info = self._calculate_age_and_flags(formatted_dob, current_date)
                        except Exception as e:
                            logger.warning(f"Error parsing date {date_str}: {e}")
                        
                        travelers.append({
                            'name': name,
                            'dob': formatted_dob,
                            **age_info
                        })
        
        return travelers
    
    def _extract_pattern23(self, matches, current_date):
        """Extract Pattern 23: Parentheses format - Name (DD/MM/YYYY), or - Name (DD/MM/YYYY),"""
        travelers = []
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                if '.' in date_str:
                    dob_date = pd.to_datetime(date_str, format='%d.%m.%Y')
                else:
                    dob_date = pd.to_datetime(date_str, format='%d/%m/%Y')
                
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers
    
    def _extract_pattern24(self, matches, current_date):
        """Extract Pattern 24: Written dates format - Name - month day, year"""
        travelers = []
        month_replacements = {
            'jan': 'january', 'feb': 'february', 'mar': 'march', 'apr': 'april',
            'may': 'may', 'jun': 'june', 'jul': 'july', 'aug': 'august',
            'sep': 'september', 'sept': 'september', 'oct': 'october',
            'nov': 'november', 'dec': 'december'
        }
        
        for name, date_str in matches:
            name = self.clean_name(name)
            if not self.validate_name_structure(name):
                continue
            
            formatted_dob = None
            age_info = {'age': None, 'is_child_by_age': False, 'is_youth_by_age': False, 'is_adult_by_age': False}
            
            try:
                # Normalize date string
                normalized_date = date_str.lower()
                for abbrev, full_name in month_replacements.items():
                    normalized_date = normalized_date.replace(abbrev, full_name)
                
                dob_date = pd.to_datetime(normalized_date, format='%B %d, %Y')
                formatted_dob = dob_date.strftime('%d/%m/%Y')
                age_info = self._calculate_age_and_flags(formatted_dob, current_date)
            except Exception as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
            
            travelers.append({
                'name': name,
                'dob': formatted_dob,
                **age_info
            })
        
        return travelers

