"""
Configuration constants for the name extraction system.

This module contains all static configuration data including:
- Reseller platform definitions
- Age category thresholds
- EU country lists
- Language and tour type mappings
- Forbidden keywords for name validation
"""

# =======================
# RESELLER PLATFORMS
# =======================

# GetYourGuide standard platforms (excluding MDA)
GYG_STANDARD_PLATFORMS = [
    'GetYourGuide',
    'GetYourGuide EC',
    'Get your Guide T&T',
    'Get your Guide Giano',
    'Get your Guide Infinity'
]

# GetYourGuide MDA platform
GYG_MDA_PLATFORM = 'Get your Guide MDA'

# All GYG platforms combined
ALL_GYG_PLATFORMS = GYG_STANDARD_PLATFORMS + [GYG_MDA_PLATFORM]


# =======================
# AGE CATEGORIES
# =======================

AGE_CHILD_MAX = 18      # Under 18 = Child
AGE_YOUTH_MIN = 18      # 18-25 = Youth
AGE_YOUTH_MAX = 25
AGE_ADULT_MIN = 25      # 25+ = Adult


# =======================
# UNIT TYPES
# =======================

UNIT_TYPE_ADULT = 'Adult'
UNIT_TYPE_CHILD = 'Child'
UNIT_TYPE_YOUTH = 'Youth'
UNIT_TYPE_INFANT = 'Infant'


# =======================
# EU COUNTRIES
# =======================

EU_COUNTRIES = {
    # Current EU member states (27 countries) - Full names
    'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 'CZECH REPUBLIC', 'CZECHIA',
    'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 'GERMANY', 'GREECE', 'HUNGARY',
    'IRELAND', 'ITALY', 'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS',
    'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAKIA', 'SLOVENIA', 'SPAIN', 'SWEDEN',

    
    # ISO 2-letter country codes for EU countries
    'AT',  # Austria
    'BE',  # Belgium
    'BG',  # Bulgaria
    'HR',  # Croatia
    'CY',  # Cyprus
    'CZ',  # Czech Republic
    'DK',  # Denmark
    'EE',  # Estonia
    'FI',  # Finland
    'FR',  # France
    'DE',  # Germany
    'GR',  # Greece
    'HU',  # Hungary
    'IE',  # Ireland
    'IT',  # Italy
    'LV',  # Latvia
    'LT',  # Lithuania
    'LU',  # Luxembourg
    'MT',  # Malta
    'NL',  # Netherlands
    'PL',  # Poland
    'PT',  # Portugal
    'RO',  # Romania
    'SK',  # Slovakia
    'SI',  # Slovenia
    'ES',  # Spain
    'SE',  # Sweden
}


# =======================
# NAME VALIDATION
# =======================

# Forbidden keywords that shouldn't appear in customer names
FORBIDDEN_NAME_KEYWORDS = [
    "Adult",
    "Child",
    "Client",
    "Traveler",
    "Travel",
    "Infant"
]

# Words to filter out when extracting names from unstructured text
INSTRUCTION_WORDS = [
    'provide', 'participants', 'group', 'birth', 'date', 
    'full', 'names', 'everyone', 'all', 'please', 'also'
]


# =======================
# LANGUAGE MAPPINGS
# =======================

# Language codes (last 3 characters of product code)
LANGUAGE_MAP = {
    'SPA': 'Spanish',
    'ITA': 'Italian',
    'FRE': 'French',
    'ENG': 'English',
    'MTL': 'Audioguide',
    'GER': 'German',
    'POR': 'Portuguese'
}


# =======================
# TOUR TYPE MAPPINGS
# =======================

# Based on product code patterns
TOUR_TYPE_PATTERNS = {
    'ROMARNSML': 'Arena Small',
    'ROMARN': 'Arena',
    'ROMCOLSML': 'Regular Small',
    'ROMCOL': 'Regular',
    'ROMVAT': 'Vatican Regular',
    'ROMBAS': 'Vatican Combo'
}


# =======================
# TICKET TYPE MAPPINGS
# =======================

TICKET_TYPE_MAP = {
    'AA': 'ARENA24',
    'A': 'ARENA',
    'R': 'REG',
    'UND':'Under Ground'
}


# =======================
# COMPANY CODE MAPPINGS
# =======================

# PNR company code to display name mappings
COMPANY_CODE_MAP = {
    'GC': 'G-CALL',
    'CC': 'C-CALL',
    'IC': 'INF-CALL',
    'MC': 'MDA-CALL',
    'TC': 'T&T-CALL',
    'DMC': 'DM-CALL',
    'OC': 'O-CALL',
    'CLC': 'CL-CALL',
    'RFTC': 'RFT-CALL',
    'MTC': 'MT-CALL',
    'GLC': 'GL-CALL',
    'LIT': 'LIT',
    'I': 'INF',
    'G': 'G',
    'GL': 'GL',
    'LM': 'LM',
    'LLM': 'LLM',
    'M': 'MDA',
    'RFT': 'RFT',
    'CL': 'CL',
    'T': 'T&T',
    'MT': 'MT',
    'DM': 'DM',
    'O': 'O',
}


# =======================
# VENTRATA COLUMN NAMES
# =======================

# Expected Ventrata columns (will be matched case-insensitively)
VENTRATA_COLUMNS = {
    'booking_reference': 'Booking Reference',
    'order_reference': 'Order Reference',
    'customer': 'Customer',
    'status': 'STATUS',
    'product': 'Product',
    'travel_date': 'Travel Date',
    'booking_date': 'Booking Date',
    'unit': 'UNIT',
    'first_name': 'Ticket Customer First Name',
    'last_name': 'Ticket Customer Last Name',
    'reseller': 'Reseller',
    'public_notes': 'Public Notes',
    'private_notes': 'Private Notes',
    'product_tags': 'Product Tags',
    'product_code': 'Product Code',
    'customer_country': 'Customer Country',
    'tour_time': 'Tour Time',
    'booking_type': 'Booking Type',
    'id': 'ID'
}


# =======================
# MONDAY COLUMN NAMES
# =======================

# Expected Monday columns (will be matched case-insensitively)
MONDAY_COLUMNS = {
    'client': 'Client',
    'order_reference': 'Order Reference',
    'change_by': 'Change By',
    'report_by': 'Report By',
    'travel_date': 'Travel Date',
    'tour_time': 'Tour Time',
    'product_code': 'Product Code',
    'ticket_time': 'Ticket Time',
    'ticket_pnr': 'Ticket PNR',
    'codice_prenotazione': 'Codice Prenotazione',
    'sigillo': 'Sigillo',
    'note': 'Note',
    'tix_source': 'TIX SOURCE',
    'ticket_group': 'TICKET GROUP',
    'missing_names': 'Missing Names',
    'adult': 'Adult',
    'child': 'Child',
    'infant': 'Infant',
    'youth': 'Youth',
    'ridotto': 'Ridotto',
    'private_notes': 'Private Notes'
}


# =======================
# REGEX PATTERNS
# =======================

# Time format patterns
TIME_PATTERN_HHMM = r'^\d{1,2}:\d{2}$'
TIME_PATTERN_HHMMSS = r'^\d{1,2}:\d{2}:\d{2}$'
TIME_PATTERN_AMPM = r'^(\d{1,2}):?(\d{0,2})\s*(AM|PM)$'
TIME_PATTERN_24H = r'^\d{3,4}$'

# PNR pattern
PNR_PATTERN = r'^([A-Za-z]{1,5})(\d{8})([A-Za-z]{1,2})(\d{4})$'
PNR_PATTERN_ALT = r'^([A-Za-z]{1,5})[-\s]?(\d{8})[-\s]?([A-Za-z]{1,2})[-\s]?(\d{4})$'

