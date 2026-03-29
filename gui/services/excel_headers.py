"""
Fast Excel header loading utilities for GUI.
"""

from __future__ import annotations

from openpyxl import load_workbook


def load_excel_headers(filepath: str) -> list[str]:
    """
    Load only first-row headers from an Excel file.

    This function is optimized for quick UI interactions:
    - read-only mode
    - first sheet only
    - first row only
    """
    workbook = load_workbook(filepath, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        row_iter = sheet.iter_rows(min_row=1, max_row=1, values_only=True)
        first_row = next(row_iter, None)
        if not first_row:
            return []

        headers = []
        for value in first_row:
            if value is None:
                continue
            header = str(value).strip()
            if header:
                headers.append(header)
        return headers
    finally:
        workbook.close()
