"""
Output column helpers for GUI advanced selection and export ordering.
"""

from __future__ import annotations

from typing import Iterable

# Default non-GUI ordering used by CLI/export fallback.
DEFAULT_OUTPUT_COLUMN_ORDER = [
    "Travel Date",
    "Full Name",
    "Order Reference",
    "Unit Type",
    "Total Units",
    "Tour Time",
    "Ticket Time",
    "Language",
    "Tour Type",
    "Private Notes",
    "Change By",
    "PNR",
    "Ticket Group",
    "Codice",
    "Sigilo",
    "TIX NOM",
    "Error",
    "Product",
    "Package Code",
    "Tag",
    "Notes",
    "Product Code",
    "Option Code",
    "ID",
    "Reseller",
    "Public Notes",
]

# Internal columns kept temporarily for formatting/export processing.
INTERNAL_HELPER_OUTPUT_COLUMNS = [
    "ID",
    "_from_update",
    "_youth_converted",
    "_tag_options",
    "_has_colosseo_tag",
    "_has_venice_tag",
]

# Mandatory columns (highlighted in Advanced UI).
MANDATORY_OUTPUT_COLUMNS = [
    "Full Name",
    "Order Reference",
    "Unit Type",
    "Error",
]

# Columns generated/extracted by app logic from Ventrata-derived processing.
# These are not always direct raw headers in the Ventrata file.
DERIVED_FROM_VENTRATA_OUTPUT_COLUMNS = [
    "Full Name",
    "Total Units",
    "Language",
    "Tour Type",
    "Tag",
    "Notes",
    "Error",
    "Ticket Time",
]

PURPLE_HIGHLIGHT_OUTPUT_COLUMNS = list(
    dict.fromkeys(MANDATORY_OUTPUT_COLUMNS + DERIVED_FROM_VENTRATA_OUTPUT_COLUMNS)
)

# Advanced options should only show columns present in Ventrata headers.
# Map Ventrata header names (case-insensitive) to output column names.
VENTRATA_HEADER_TO_OUTPUT_COLUMN = {
    "travel date": "Travel Date",
    "order reference": "Order Reference",
    "unit": "Unit Type",
    "tour time": "Tour Time",
    "private notes": "Private Notes",
    "public notes": "Public Notes",
    "product": "Product",
    "product code": "Product Code",
    "package option": "Package Code",
    "package code": "Package Code",
    "option code": "Option Code",
    "reseller": "Reseller",
}

_CANONICAL_COLUMN_BY_CASEFOLD = {
    col.casefold(): col for col in DEFAULT_OUTPUT_COLUMN_ORDER
}
_HEADER_TO_OUTPUT_BY_CASEFOLD = {
    header.casefold(): output_col
    for header, output_col in VENTRATA_HEADER_TO_OUTPUT_COLUMN.items()
}


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def canonicalize_column_name(column_name: str | None) -> str | None:
    if not isinstance(column_name, str):
        return None
    stripped = column_name.strip()
    if not stripped:
        return None

    # If it's a known Ventrata header, map to output name.
    mapped = _HEADER_TO_OUTPUT_BY_CASEFOLD.get(stripped.casefold())
    if mapped:
        return mapped

    # Otherwise treat as output column label.
    canonical = _CANONICAL_COLUMN_BY_CASEFOLD.get(stripped.casefold())
    return canonical


def map_ventrata_headers_to_output_columns(headers: Iterable[str]) -> list[str]:
    """
    Convert Ventrata header names into available advanced output columns.
    Keeps file header order first, then app-derived and mandatory columns.
    """
    mapped = []
    for header in headers:
        canonical = canonicalize_column_name(header)
        if canonical:
            mapped.append(canonical)

    mapped = dedupe_preserve_order(mapped)
    mapped_set = set(mapped)
    combined = mapped + [
        col for col in (DERIVED_FROM_VENTRATA_OUTPUT_COLUMNS + MANDATORY_OUTPUT_COLUMNS)
        if col not in mapped_set
    ]
    return dedupe_preserve_order(combined)


def reconcile_selected_columns(
    selected_columns: Iterable[str] | None,
    available_columns: Iterable[str] | None,
) -> list[str]:
    """
    Reconcile selection with available columns:
    - keep available selected columns in their saved order
    - append newly available columns at the end
    - if nothing survives, select all available columns
    """
    available = dedupe_preserve_order(
        canonical for canonical in (
            canonicalize_column_name(col) for col in (available_columns or [])
        ) if canonical
    )
    selected = dedupe_preserve_order(
        canonical for canonical in (
            canonicalize_column_name(col) for col in (selected_columns or [])
        ) if canonical
    )

    available_set = set(available)
    kept_selected = [col for col in selected if col in available_set]
    selected_set = set(kept_selected)
    new_available = [col for col in available if col not in selected_set]

    reconciled = kept_selected + new_available
    if not reconciled and available:
        return list(available)
    return reconciled


def resolve_selected_output_columns(
    existing_columns: Iterable[str],
    selected_columns: Iterable[str] | None,
) -> list[str]:
    """
    Strict GUI output order: selected_order ∩ existing_result_columns.
    """
    existing = set(existing_columns)
    selected_order = dedupe_preserve_order(
        canonical for canonical in (
            canonicalize_column_name(col) for col in (selected_columns or [])
        ) if canonical
    )
    return [col for col in selected_order if col in existing]
