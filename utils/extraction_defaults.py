"""Offline baseline for the supported extraction rule schema.

Cloud edits belong in cloudflare-worker/src/extraction_rules.json.
"""

import copy
import config

SETTINGS_KEYS = (
    'GYG_STANDARD_PLATFORMS',
    'GYG_MDA_PLATFORM',
    'AGE_CHILD_MAX',
    'AGE_YOUTH_MIN',
    'AGE_YOUTH_MAX',
    'AGE_ADULT_MIN',
    'INFANT_TO_CHILD_PRODUCT_TAGS',
    'EU_COUNTRIES',
    'FORBIDDEN_NAME_KEYWORDS',
    'GYG_RESELLER_MARKERS',
    'LANGUAGE_MAP',
    'TOUR_TYPE_PATTERNS',
    'TICKET_TYPE_MAP',
    'COMPANY_CODE_MAP',
)

PATTERNS = {
    "gyg_name": {
        "regex": "(?:First Name:|First name:)\\s*([^\\n:]+)\\s*(?:Last Name:|Last name:)\\s*([^\\n:]+)",
        "flags": 2,
        "groups": 2
    },
    "gyg_dob_slash": {
        "regex": "Date of Birth:\\s*(\\d{2}/\\d{2}/\\d{4})",
        "flags": 2,
        "groups": 1
    },
    "gyg_dob_dash": {
        "regex": "Date of Birth:\\s*(\\d{4}-\\d{2}-\\d{2})",
        "flags": 2,
        "groups": 1
    },
    "viator_dob": {
        "regex": "Q:\\s*Date of Birth\\s*\\n\\s*A:\\s*([^\\n]+)",
        "flags": 10,
        "groups": 1
    },
    "viator_dob_inline": {
        "regex": "Q:\\s*Date of Birth[^\\n]*A:\\s*([^\\n]+)",
        "flags": 2,
        "groups": 1
    }
}

MDA_PATTERNS = {
    "PATTERN_TRAVELER": {
        "regex": "Traveler \\d+:",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_INSTRUCTION_WORDS": {
        "regex": "\\b(?:provide|participants|group|birth|date|full|names|everyone|all|please)\\b",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_DDMMYYYY_DOT": {
        "regex": "\\d{1,2}\\.\\d{1,2}\\.\\d{4}",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_NAME_DATE_DOT": {
        "regex": "[A-Za-zÀ-ÿ\\s\\-\\'\\.]+\\s+\\d{1,2}\\.\\d{1,2}\\.\\d{4}",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_DDMMYYYY_DOT_END": {
        "regex": "\\d{1,2}\\.\\d{1,2}\\.\\d{4}\\.",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_NAME_DATE_SLASH": {
        "regex": "[A-Za-zÀ-ÿ\\s\\-\\'\\.]+\\s+\\d{1,2}/\\d{1,2}/\\d{4}\\.?",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_NAME_PAREN_DATE": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*\\((\\d{1,2}/\\d{1,2}/\\d{2,4})\\)",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_PAREN_YYYYMMDD": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*\\((\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.?)\\)",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_ADULT_CHILD_DATE": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*\\((adult|child)\\)\\s*(\\d{1,2}-\\d{1,2}-\\d{4})",
        "flags": 2,
        "groups": 3
    },
    "PATTERN_NAME_DDMMMYYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*\\((\\d{1,2}[a-zA-Z]{3}\\d{4})\\)",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_YYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*\\((\\d{4})\\)",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_DDMMYYYY_DOT_LINE": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+?)\\s+(\\d{1,2}\\.\\d{1,2}\\.\\d{4})\\.?",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_COMMA_DDMMYYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+),\\s*(\\d{1,2}\\.\\d{1,2}\\.\\d{4}\\.?)",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_SLASH_DDMMYYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)/\\s*(\\d{1,2}\\.\\d{1,2}\\.\\d{4})",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_MONTH_DAY_YEAR": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s+([A-Za-z]+)\\s+(\\d{1,2}),\\s*(\\d{4})",
        "flags": 0,
        "groups": 4
    },
    "PATTERN_NAME_D_M_YYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s+(\\d{1,2})\\.\\s*(\\d{1,2})\\.\\s*(\\d{4})",
        "flags": 0,
        "groups": 4
    },
    "PATTERN_NAME_DD_MONTH_YYYY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s+(\\d{1,2}\\s+[A-Za-z]+\\s+\\d{4})",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_DD_MM_YYYY_DASH": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s+(\\d{1,2}-\\d{1,2}-\\d{4})",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_NAME_DOB_EXTENDED": {
        "regex": "([A-Za-zÀ-ÿĀ-žА-я\\u00C0-\\u017F\\u1E00-\\u1EFF\\u0100-\\u024F\\s\\-\\'.]{3,50})\\s*-\\s*(?:DOB\\s*)?(\\d{1,2}(?:st|nd|rd|th)?\\s+[A-Za-z]+\\s+\\d{4}|\\d{1,2}[/\\.]\\d{1,2}[/\\.]\\d{4})",
        "flags": 2,
        "groups": 2
    },
    "PATTERN_NAME_PAREN_DATE_EXTENDED": {
        "regex": "-?\\s*([A-Za-zÀ-ÿĀ-žА-я\\u00C0-\\u017F\\u1E00-\\u1EFF\\u0100-\\u024F\\s\\-\\'.]{3,50})\\s*\\((\\d{1,2}[/\\.]\\d{1,2}[/\\.]\\d{4})\\)\\s*,?",
        "flags": 2,
        "groups": 2
    },
    "PATTERN_NAME_WRITTEN_DATE": {
        "regex": "([A-Za-zÀ-ÿĀ-žА-я\\u00C0-\\u017F\\u1E00-\\u1EFF\\u0100-\\u024F\\s\\-\\'.]{3,50})\\s*-\\s*([a-zA-Z]+\\s+\\d{1,2},\\s+\\d{4})",
        "flags": 2,
        "groups": 2
    },
    "PATTERN_FRENCH_AGE": {
        "regex": "-\\s*([A-Za-zÀ-ÿ\\s\\-\\'\\.]+)\\s*:\\s*(\\d+)\\s*ans?",
        "flags": 2,
        "groups": 2
    },
    "PATTERN_ORDINAL_DATE": {
        "regex": "\\d{1,2}(?:st|nd|rd|th)\\s+[A-Za-z]+\\s+\\d{4}",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_VALID_NAME_WORD": {
        "regex": "^[A-Za-zÀ-ÿ'\\.\\-]+$",
        "flags": 0,
        "groups": 0
    },
    "PATTERN_FLOOR": {
        "regex": "^\\d+(?:st|nd|rd|th)?\\s+floor",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_RMZ": {
        "regex": "^RMZ",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_NAME_DATE_MULTILINE": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+?)(?:\\s+(\\d{1,2}/\\d{1,2}/\\d{2,4}))?\\s*(?=\\n|$)",
        "flags": 8,
        "groups": 2
    },
    "PATTERN_FIRST_NAME": {
        "regex": "First Name:\\s*([^\\n:]+)",
        "flags": 2,
        "groups": 1
    },
    "PATTERN_LAST_NAME": {
        "regex": "Last Name:\\s*([^\\n:]+)",
        "flags": 2,
        "groups": 1
    },
    "PATTERN_DOB_ISO": {
        "regex": "Date of Birth:\\s*(\\d{4}-\\d{2}-\\d{2})",
        "flags": 2,
        "groups": 1
    },
    "PATTERN_ORDINAL_ENTRY": {
        "regex": "^(.+?)\\s+(\\d{1,2}(?:st|nd|rd|th)\\s+[A-Za-z]+\\s+\\d{4})$",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_DDMMMYYYY_MATCH": {
        "regex": "^(\\d{1,2})([a-zA-Z]{3})(\\d{4})$",
        "flags": 0,
        "groups": 3
    },
    "PATTERN_AND_SPLIT": {
        "regex": "\\s+and\\s+",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_INSTRUCTION_WORDS_EXTENDED": {
        "regex": "\\b(?:provide|participants|group|birth|date|full|names|everyone|all|please|also|and)\\b",
        "flags": 2,
        "groups": 0
    },
    "PATTERN_PATTERN20_ENTRY": {
        "regex": "^(.+?)\\s+(\\d{1,2}\\.\\d{1,2}\\.\\d{4})\\.?$",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_PATTERN21_ENTRY": {
        "regex": "([A-Za-zÀ-ÿ\\s\\-\\'\\.]+?)\\s+(\\d{1,2}/\\d{1,2}/\\d{4})\\.?",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_PATTERN22_ENTRY": {
        "regex": "^(.+?)\\s+(\\d{1,2}\\.\\d{1,2}\\.\\d{4})\\.?$",
        "flags": 0,
        "groups": 2
    },
    "PATTERN_ORDINAL_CLEAN": {
        "regex": "(\\d+)(?:st|nd|rd|th)",
        "flags": 0,
        "groups": 1
    },
    "PATTERN_TRAILING_COMMA_SPACE": {
        "regex": "[,\\s]+$",
        "flags": 0,
        "groups": 0
    }
}


def default_rules():
    settings = {key: getattr(config, key) for key in SETTINGS_KEYS}
    settings["EU_COUNTRIES"] = sorted(settings["EU_COUNTRIES"])
    return copy.deepcopy({
        "version": 1,
        "revision": "bundled-2026-11-14.1",
        "settings": settings,
        "patterns": PATTERNS,
        "mda_patterns": MDA_PATTERNS,
    })
