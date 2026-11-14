"""
Ventrata export column names, shared with Crown Report.

Both apps read the same Ventrata export, so the column names come from one place:
the `ventrata.input_columns` section of Crown Report's extraction rules, served by
its Cloudflare Worker at /rules/extraction. When Ventrata renames a column, edit
that section (internal name -> export name) and deploy the Worker; neither app
needs a rebuild.

The last good download is cached so the app keeps working offline. With no
download and no cache, the export is read with its own headers unchanged.
"""

import json
import logging
import os

import requests
import yaml

logger = logging.getLogger(__name__)

EXTRACTION_RULES_URL = "https://crown-report-config.navid-kill-policy.workers.dev/rules/extraction"
CACHE_PATH = os.path.join(os.path.expanduser("~"), ".name_extractor_ventrata_columns.json")

# Internal names the extraction code works with; the rules must name an export column for each.
REQUIRED_COLUMNS = (
    'Reseller', 'Order Reference', 'Unit', 'Public Notes', 'Private Notes', 'Travel Date',
    'Product Code', 'Customer Country', 'Ticket Customer First Name', 'Ticket Customer Last Name',
)

# Where the mapping in use came from: "cloud", "cached" or "none".
_last_source = "none"
_last_revision = ""


def _validate(input_columns):
    """Return the mapping if it is a usable internal name -> export name map, else raise ValueError."""
    if not isinstance(input_columns, dict) or not input_columns:
        raise ValueError("ventrata.input_columns is missing or empty")
    for internal_name, export_name in input_columns.items():
        if not isinstance(internal_name, str) or not isinstance(export_name, str) or not export_name.strip():
            raise ValueError(f"ventrata.input_columns has an invalid entry: {internal_name!r}: {export_name!r}")
    missing = [name for name in REQUIRED_COLUMNS if name not in input_columns]
    if missing:
        raise ValueError(f"ventrata.input_columns has no export column for {missing}")
    return input_columns


def _download(timeout):
    response = requests.get(
        EXTRACTION_RULES_URL,
        headers={"Accept": "application/yaml, text/yaml, text/plain", "Cache-Control": "no-cache"},
        timeout=timeout,
    )
    response.raise_for_status()
    document = yaml.safe_load(response.text)
    if not isinstance(document, dict):
        raise ValueError("extraction rules are not a YAML mapping")
    ventrata = document.get("ventrata")
    if not isinstance(ventrata, dict):
        raise ValueError("extraction rules have no ventrata section")
    return _validate(ventrata.get("input_columns")), str(document.get("revision", ""))


def _read_cache():
    with open(CACHE_PATH, "r", encoding="utf-8") as handle:
        cached = json.load(handle)
    return _validate(cached.get("input_columns")), str(cached.get("revision", ""))


def _write_cache(input_columns, revision):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump({"revision": revision, "input_columns": input_columns}, handle, indent=2)
    except OSError as e:
        logger.warning(f"Could not cache the Ventrata column names: {e}")


def get_ventrata_input_columns(timeout=5):
    """
    Get the Ventrata column mapping (internal name -> export name).

    Tries the Worker first, then the last cached copy. Returns an empty dict when
    neither is available, which leaves the export's headers as they are.
    """
    global _last_source, _last_revision

    try:
        input_columns, revision = _download(timeout)
        _write_cache(input_columns, revision)
        _last_source, _last_revision = "cloud", revision
        logger.info(f"Using Ventrata column names from the cloud (revision {revision})")
        return input_columns
    except Exception as e:
        logger.warning(f"Could not download the Ventrata column names: {e}")

    try:
        input_columns, revision = _read_cache()
        _last_source, _last_revision = "cached", revision
        logger.info(f"Using cached Ventrata column names (revision {revision})")
        return input_columns
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Ignoring an unreadable Ventrata column cache: {e}")

    _last_source, _last_revision = "none", ""
    logger.warning("No Ventrata column names available - reading the export's headers unchanged")
    return {}


def get_ventrata_columns_source():
    """Return (source, revision) of the mapping used by the last get_ventrata_input_columns call."""
    return _last_source, _last_revision


def rename_ventrata_columns(df, input_columns):
    """
    Rename a Ventrata export's columns to the internal names the code works with.

    Export names are matched case-insensitively, as everywhere else in this app.
    A column is left alone when the file already has its internal name, so an
    export in the old layout reads exactly as before.
    """
    by_lower = {str(col).strip().lower(): col for col in df.columns}
    existing = set(by_lower)
    renames = {}
    for internal_name, export_name in input_columns.items():
        actual = by_lower.get(export_name.strip().lower())
        if actual is None or str(actual).strip().lower() == internal_name.lower():
            continue
        if internal_name.lower() in existing:
            logger.warning(
                f"Ventrata file has both '{actual}' and '{internal_name}' - keeping '{internal_name}'"
            )
            continue
        renames[actual] = internal_name
    if renames:
        logger.info(f"Renamed Ventrata columns: {renames}")
    return df.rename(columns=renames)
