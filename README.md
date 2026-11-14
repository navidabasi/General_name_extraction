# Names Generation System

## Features

- **Platform-Specific Extractors**: Separate handlers for GYG Standard, GYG MDA (24 patterns), and Non-GYG resellers
- **Comprehensive Validation**: Multiple layers of error detection and flagging
- **DOB/Age Processing**: Automatic age calculation and unit type assignment
- **Youth Validation**: EU-specific validation for youth bookings (18-25 age range)
- **Duplicate Detection**: Identifies duplicate names within bookings
- **Forbidden Content Checking**: Flags suspicious names with keywords, digits, or single letters
- **Case-Insensitive**: Handles column names regardless of capitalization

## Project Structure

```
namesgen/
├── main.py                      # Entry point
├── config.py                    # Configuration constants
├── data_loader.py               # Data loading and merging
├── processor.py                 # Main orchestration
├── utils/
│   ├── __init__.py
│   ├── normalization.py         # Data normalization utilities
│   └── age_calculator.py        # DOB/age calculations
├── extractors/
│   ├── __init__.py
│   ├── base_extractor.py        # Base class
│   ├── gyg_standard.py          # GYG Standard platforms
│   ├── gyg_mda.py               # GYG MDA (24 patterns)
│   ├── non_gyg.py               # Non-GYG resellers
│   └── spacy_fallback.py        # AI fallback using Spacy NLP
└── validators/
    ├── __init__.py
    ├── name_validator.py        # Name content validation
    ├── duplicate_validator.py   # Duplicate detection
    ├── youth_validator.py       # Youth/age validation
    └── unit_validator.py        # Unit count validation
```

## Installation

```bash
# Install required packages
pip install -r requirements.txt

# Setup Spacy model for AI fallback extraction (recommended)
python -m spacy download en_core_web_sm
```

**⚠️ Important - Python Version Compatibility:**

The Spacy NLP fallback feature requires **Python 3.11 or 3.12**. It is **not compatible** with Python 3.14+ due to Pydantic v1 limitations.

- ✅ **Python 3.11 or 3.12**: Full functionality including Spacy fallback
- ⚠️ **Python 3.14+**: All features work EXCEPT Spacy fallback (standard extractors still work fine)

**Note:** The Spacy fallback feature requires the `en_core_web_sm` model. Install it with:

```bash
python -m spacy download en_core_web_sm
```

If Spacy is not available, the system will automatically skip the fallback and log a warning.

## Usage

### 🎨 GUI Mode (Recommended)

**Easy-to-use graphical interface:**

```bash
python gui_app.py
```

**Features:**
- 🖱️ Click to select files
- 📊 Real-time progress tracking
- ✅ Visual validation indicators
- ⚠️ Collapsible warnings panel
- 🎯 Choose output location with dialog
- 📁 Auto-numbered output files

## Cloud configuration

Ventrata headers are shared with Crown Report. Name Extractor's extraction rules are maintained separately.

| Configuration | Maintained source | Live endpoint |
|---|---|---|
| Shared Ventrata headers | Crown Report: `cloudflare-worker/src/extraction_rules.yaml`, only `ventrata.input_columns` | [Crown Report rules](https://crown-report-config.navid-kill-policy.workers.dev/rules/extraction) |
| Name Extractor rules | [`cloudflare-worker/src/extraction_rules.json`](cloudflare-worker/src/extraction_rules.json) | [Name Extractor rules](https://name-extractor-config.navid-kill-policy.workers.dev/rules/extraction) |

When Ventrata renames a header, change the **right-hand value** in Crown Report's `ventrata.input_columns`, bump its revision, and deploy the Crown Report Worker. Both apps then receive the same header mapping. Do not copy Crown Report's extraction algorithms into Name Extractor's rules.

The Name Extractor document controls:

- GYG reseller lists and substring matching markers.
- GYG Standard name and DOB patterns, Viator DOB labels, and the existing MDA regex patterns.
- Age boundaries, EU countries, forbidden name keywords, and Infant-to-Child product tags.
- Language, tour type, ticket type, and PNR company mappings.

The existing Python extraction strategies, priority order, private-note parser, date parsers, and error messages remain in application code. Supported pattern/setting edits need only a Worker deployment; new strategies or schema capabilities need an application release. Keep each pattern's capture-group count and meaning unchanged. For example, GYG names require first name followed by last name; DOB patterns must still return formats understood by the date parser.

To publish a Name Extractor rule change, edit its JSON, bump `revision`, validate, and deploy:

```bash
python -m unittest discover -s tests -q
cd cloudflare-worker
npm install
npm run check
npm run deploy
```

Inspect `/rules/extraction` after deployment. Start another extraction in the app to refresh both sources; the download happens in the processing thread. Logs show sources and revisions. The GUI warning panel reports fallback use.

Validated downloads are saved atomically to:

- `~/.name_extractor_ventrata_columns.json` — shared headers.
- `~/.name_extractor_rules.json` — Name Extractor rules.

Invalid downloads never overwrite a good cache. If the Name Extractor Worker and cache are unavailable, the app uses its original extraction defaults (`config.py` and `utils/extraction_defaults.py`). Header mapping has no bundled copy: without cloud/cache, only the original header layout can load. Only configuration is downloaded; the Worker receives no spreadsheet content.

### macOS migration

An existing `.app` built before these loaders were added needs **one new build** to adopt cloud updates. Deploying the Worker cannot change Python code inside an older bundle. The repository's existing bundled application is preserved; this change updates source code and build specifications only.

Run the updated source now with:

```bash
python -m pip install -r requirements.txt
python gui_app.py
```

For a later application release, install PyInstaller and use `gui_app_macos.spec` on macOS or `gui_app_windows.spec` on Windows. Both specifications check and include PyYAML and the cloud loaders. Build output replaces distribution files, so perform that separately when preparing a release.

## Input File Requirements

### Ventrata File Columns

Both the original Ventrata headers and the renamed export headers are accepted. The shared cloud mapping converts export headers into these internal names (case-insensitive).

Required columns:
- `Order Reference`, `Reseller`, `UNIT`, `ID`
- `Ticket Customer First Name`, `Ticket Customer Last Name`
- `Public Notes`, `Private Notes`

Other supported columns:
- `Booking Reference`, `Customer`, `STATUS`, `Product`
- `Travel Date`, `Booking Date`, `Tour Time`, `Booking Type`
- `Product Tags`, `Product Code`, `Customer Country`
- `Package Option`, `Option Code`

A missing-column error means a required header could not be found after mapping; it does not mean that the Excel file extension is wrong. A first run with renamed headers needs internet access to obtain the shared layout. After a successful download, the last valid layout works offline.

### Monday File Columns (Optional)

Required columns (case-insensitive):
- `Order Reference` - For merging with Ventrata

Expected columns:
- `Client`, `Change By`, `Report By`
- `Travel Date`, `Tour Time`, `Product Code`
- `Ticket Time`, `Ticket PNR`
- `Codice Prenotazione`, `Sigillo`
- `Note`, `TIX SOURCE`, `TICKET GROUP`
- `Missing Names`, `Adult`, `Child`, `Infant`, `Youth`, `Ridotto`
- `Private Notes`

## Output Format

**Check the output**:
   - Results are saved to `names_output.xlsx`
   - Logs are saved to `namesgen.log`

The system generates a DataFrame/Excel file with the following columns:

| Column | Description |
|--------|-------------|
| Full Name | Extracted customer name |
| Order Reference | Booking reference |
| Travel Date | Tour date (from Ventrata) |
| Unit Type | Assigned unit type (Adult/Child/Youth/Infant) |
| Total Units | Total travelers in booking |
| Tour Time | Normalized tour time (HH:MM) |
| Language | Extracted from product code |
| Tour Type | Extracted from product code |
| Private Notes | Original private notes |
| Reseller | Platform name |
| Error | Validation errors (pipe-separated) |

**Additional columns when Monday file is provided:**

| Column | Description |
|--------|-------------|
| PNR | Ticket PNR from Monday |
| Ticket Group | Ticket Group from Monday |
| TIX NOM | Generated from PNR |

## Error Types

The system detects and flags the following errors:

### Unit/Traveler Mismatches
- `Number of provided units (X) and Travelers (Y) in the booking does not match`

### Missing Information
- `GYG booking no Date of Birth indicated`
- `GYG MDA booking missing some DOBs for child tickets`
- `No names could be extracted from GYG booking`

### Name Issues
- `Please Check Names before Insertion` - Name contains forbidden keywords, digits, or single letters
- `Duplicated names in the booking: Name1, Name2`

### Youth Validation (EU only)
- `Youth in the booking` - Simple flag for youth presence
- `Youth unit mismatch: X youth units booked but Y travelers in youth age range`
- `Youth is outside of 18-25 Range`

### Age/Unit Mismatches
- `Adult has child ticket`
- `Child has adult ticket`
- `All travelers under 18 with mixed unit types`
- `Booking has only Child/Infant units`

## How It Works

### 1. Name Extraction by Platform

#### GYG Standard Platforms
- Extracts from structured format: `First Name: X\nLast Name: Y`
- DOBs: `Date of Birth: DD/MM/YYYY` or `Date of Birth: YYYY-MM-DD`

#### GYG MDA Platform
Tries 24 patterns in priority order:
1. Structured format with "Traveler X:"
2-22. Various date formats (comma-separated, parentheses, dashes, dots, etc.)
23-24. Names without dates (last resort)

#### Non-GYG Platforms
- Uses structured columns: `Ticket Customer First Name` + `Ticket Customer Last Name`
- No pattern matching required


### 2. Age Calculation and Unit Assignment

```
Age < 18: Child
Age 18-25: Youth
Age > 25: Adult
```

Unit types are assigned based on DOB and age, with youngest travelers receiving Child units first.

### 3. Validation Layers

1. **Pre-processing**: Calculate booking-level errors once
2. **Extraction**: Validate name structure during extraction
3. **Post-processing**: Check for duplicates and forbidden content
4. **Youth validation**: EU-specific age range validation

### 4. Error Aggregation

Multiple errors are combined with ` | ` separator:
```
"GYG booking no Date of Birth indicated | Youth in the booking"
```

## Logging

Logs are written to both console and `namesgen.log` file:
- `INFO`: Processing progress and statistics
- `WARNING`: Data issues (missing DOBs, parse failures)
- `ERROR`: Critical failures
- `DEBUG`: Detailed extraction information


