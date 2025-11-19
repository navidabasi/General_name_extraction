# Spacy Fallback Extraction - Implementation Guide

## Overview

The Spacy fallback extractor provides AI-powered name extraction as a last resort when traditional structured extraction methods fail. It uses Spacy's Named Entity Recognition (NER) to extract person names from unstructured text in Public Notes.

## When It's Used

### Automatic Fallback Triggers

1. **GYG Bookings**: 
   - After GYG Standard extraction returns no names
   - AND after GYG MDA extraction returns no names
   - Then Spacy fallback is attempted

2. **Non-GYG Bookings**:
   - When structured name fields (First Name + Last Name) are empty
   - Then Spacy fallback is attempted

## How It Works

### 1. Name Extraction

The extractor uses Spacy's NER to identify PERSON entities in the public notes:

```python
doc = nlp(public_notes)
for ent in doc.ents:
    if ent.label_ == "PERSON":
        # Extract and validate name
```

### 2. Context Analysis

For each extracted name, the system captures surrounding text (50 characters before and after) to identify unit type keywords:

**Unit Type Keywords:**

- **Adult**: "adult", "adults", "grown-up", "parent", "guardian", "mother", "father", "mom", "dad"
- **Child**: "child", "children", "kid", "kids", "minor", "son", "daughter", "boy", "girl"
- **Infant**: "infant", "infants", "baby", "babies", "toddler", "toddlers"
- **Youth**: "youth", "youths", "teen", "teens", "teenager", "student"

### 3. Unit Type Assignment

#### Non-Mixed Bookings (Single Unit Type)

All extracted names get the single available unit type:

```
Booking: 3 Adults
Names extracted: John Smith, Mary Jones, Bob Wilson
Result: All assigned "Adult"
```

#### Mixed Bookings (Multiple Unit Types)

1. **Keyword-Based Assignment**: Names with nearby keywords get suggested unit types
2. **Remaining Pool Assignment**: Names without keywords get assigned from remaining units

**Example:**

```
Public Notes:
"Tour for John Smith (adult), Mary Smith (adult), Tommy Smith (child age 8)"

Booking Units: 2 Adults, 1 Child

Process:
1. John Smith → "adult" keyword found → Assigned Adult
2. Mary Smith → "adult" keyword found → Assigned Adult  
3. Tommy Smith → "child" keyword found → Assigned Child
```

## Implementation Details

### File Structure

```
extractors/
├── spacy_fallback.py       # Main implementation
└── __init__.py            # Exports SpacyFallbackExtractor

processor.py                # Integrated fallback logic
```

### Key Classes and Methods

#### `SpacyFallbackExtractor`

**Main Methods:**

- `extract_travelers(public_notes, order_ref, booking_data)` - Main extraction method
- `_extract_person_entities(text, order_ref)` - NER extraction
- `_determine_unit_from_context(context, is_mixed_units, unit_counts)` - Keyword detection
- `_assign_final_unit_types(travelers, unit_counts, is_mixed_units, order_ref)` - Final assignment

**Return Format:**

```python
[
    {
        'name': 'John Smith',
        'dob': None,
        'age': None,
        'is_child_by_age': False,
        'is_youth_by_age': False,
        'is_adult_by_age': False,
        'unit_type': 'Adult'  # Assigned by fallback
    },
    # ... more travelers
]
```

### Integration in Processor

The processor (`processor.py`) integrates Spacy fallback in `_process_booking()`:

```python
# GYG bookings
if not travelers:
    # Standard failed, try MDA
    travelers = extractors['gyg_mda'].extract_travelers(...)
    
    if not travelers:
        # MDA failed, try Spacy
        travelers = extractors['spacy_fallback'].extract_travelers(...)

# Non-GYG bookings  
if not travelers:
    # Structured extraction failed, try Spacy
    travelers = extractors['spacy_fallback'].extract_travelers(...)
```

## Requirements

### Python Version

⚠️ **Important**: Spacy 3.7.0 requires Python 3.11 or 3.12

- ✅ **Python 3.11-3.12**: Fully supported
- ❌ **Python 3.14+**: Not compatible (Pydantic v1 limitation)
- ❌ **Python 3.10 or lower**: May have limited support

### Dependencies

```
spacy==3.7.0
en_core_web_sm (Spacy model)
```

### Installation

```bash
# Install Spacy
pip install spacy==3.7.0

# Download English model
python -m spacy download en_core_web_sm

# OR use the setup script
python setup_spacy.py
```

## Error Handling

### Graceful Degradation

The system handles missing Spacy gracefully:

```python
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("Spacy not available. Fallback extraction disabled.")
```

If Spacy is not available:
- Warning is logged
- Fallback extraction is skipped
- Standard extractors continue to work normally
- No crashes or errors

### Model Not Found

If Spacy is installed but model is missing:

```python
try:
    self.nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Spacy model 'en_core_web_sm' not found")
    self.nlp = None
```

Extraction will return empty list with appropriate logging.

## Testing

### Test Script

Use `test_spacy_fallback.py` to verify the installation:

```bash
python test_spacy_fallback.py
```

**Output:**
- Checks Spacy availability
- Checks model availability  
- Tests extraction with sample data
- Tests non-mixed and mixed unit scenarios

### Manual Testing

```python
from extractors.spacy_fallback import SpacyFallbackExtractor

extractor = SpacyFallbackExtractor()

public_notes = "Tour with John Smith (adult) and Tommy Smith (child)"
booking_data = {'unit_counts': {'Adult': 1, 'Child': 1}}

travelers = extractor.extract_travelers(public_notes, "TEST-001", booking_data)

for t in travelers:
    print(f"{t['name']} → {t['unit_type']}")
```

## Limitations

### 1. Accuracy

Spacy NER is generally accurate but may:
- Miss names in unusual formats
- Extract non-person entities as names
- Fail on heavily abbreviated text

### 2. No DOB Extraction

Fallback extraction cannot extract dates of birth:
- `dob` is always `None`
- `age` is always `None`
- Age-based validation is not possible

### 3. Context Dependency

Unit type assignment depends on:
- Quality of public notes text
- Presence of unit type keywords
- Proximity of keywords to names

### 4. Language Support

Currently only supports English:
- Uses `en_core_web_sm` model
- Non-English names may be missed
- Non-English text may reduce accuracy

## Troubleshooting

### "Spacy not available" Warning

**Cause**: Spacy package not installed

**Solution**:
```bash
pip install spacy==3.7.0
```

### "Spacy model not found" Warning

**Cause**: Model `en_core_web_sm` not downloaded

**Solution**:
```bash
python -m spacy download en_core_web_sm
```

### Pydantic/Python 3.14 Error

**Cause**: Spacy 3.7.0 not compatible with Python 3.14+

**Solution**: Use Python 3.11 or 3.12:
```bash
# Create new virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### No Names Extracted

**Possible causes**:
1. Public notes contain no person names
2. Names in unusual format Spacy doesn't recognize
3. Text is too abbreviated or fragmented

**Solution**: Check public notes content and format

## Performance

### Speed

Spacy processing is fast but slower than regex:
- ~10-50ms per booking (depending on text length)
- Acceptable for batch processing
- May add noticeable delay for very large datasets

### Memory

Spacy model requires ~50MB RAM when loaded:
- Model loaded once at initialization
- Shared across all extractions
- Not a concern for most systems

## Future Enhancements

Possible improvements:

1. **Multi-language support**: Load models for other languages
2. **DOB extraction**: Add regex patterns for date extraction from context
3. **Improved keywords**: Expand keyword lists based on real-world data
4. **Confidence scores**: Use Spacy's confidence scores for validation
5. **Custom NER training**: Train custom model on booking data

## Summary

The Spacy fallback extractor provides a robust last-resort method for name extraction when structured methods fail. It:

✅ Works automatically as a fallback
✅ Handles both GYG and non-GYG bookings
✅ Assigns unit types intelligently based on context
✅ Fails gracefully when not available
✅ Requires minimal configuration

⚠️ Requires Python 3.11-3.12
⚠️ Cannot extract DOBs
⚠️ Depends on text quality

It's a valuable addition to the extraction pipeline, especially for handling edge cases and malformed data.

