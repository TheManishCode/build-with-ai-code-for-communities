"""Parser for Excel 2003 SpreadsheetML files that the LGD portal exports with a
misleading ``.xls`` extension (they are XML, not a binary Excel file — xlrd/openpyxl
cannot open them).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
INDEX_ATTR = "{urn:schemas-microsoft-com:office:spreadsheet}Index"


def iter_rows(path: Path | str, sheet_index: int = 0) -> list[dict[int, str | None]]:
    """Return every row in the worksheet as a dict of {1-based column index: cell text}."""
    tree = ET.parse(path)
    worksheets = tree.getroot().findall("ss:Worksheet", NS)
    table = worksheets[sheet_index].find("ss:Table", NS)
    rows = []
    for row in table.findall("ss:Row", NS):
        cells: dict[int, str | None] = {}
        col = 0
        for cell in row.findall("ss:Cell", NS):
            idx_attr = cell.get(INDEX_ATTR)
            col = int(idx_attr) if idx_attr else col + 1
            data = cell.find("ss:Data", NS)
            cells[col] = data.text if data is not None else None
        rows.append(cells)
    return rows


def find_data_rows(
    rows: list[dict[int, str | None]], header_token: str, sno_col: int = 1
) -> tuple[dict[int, str | None], list[dict[int, str | None]]]:
    """Locate the header row (last row in the first 10 containing header_token) and
    return (header_row, data_rows), skipping any sub-header/annotation rows between
    the header and the first row whose sno_col cell parses as an increasing integer.
    """
    header_idx = None
    for i, row in enumerate(rows[:10]):
        if any(v == header_token for v in row.values()):
            header_idx = i
    if header_idx is None:
        raise ValueError(f"header token {header_token!r} not found in first 10 rows")

    def _looks_numeric(val: str | None) -> bool:
        if val is None:
            return False
        try:
            float(val.strip())
            return True
        except ValueError:
            return False

    data_start = header_idx + 1
    while data_start < len(rows):
        if _looks_numeric(rows[data_start].get(sno_col)):
            break
        data_start += 1
    return rows[header_idx], rows[data_start:]


def assert_header(header_row: dict[int, str | None], expected: dict[int, str]) -> None:
    """Fail loudly if the column at a given index isn't what we expect, rather than
    silently ingesting misaligned data."""
    mismatches = []
    for idx, expected_name in expected.items():
        actual = (header_row.get(idx) or "").strip()
        if actual != expected_name.strip():
            mismatches.append(f"col {idx}: expected {expected_name!r}, found {actual!r}")
    if mismatches:
        raise ValueError("Header mismatch — schema may have changed:\n" + "\n".join(mismatches))
