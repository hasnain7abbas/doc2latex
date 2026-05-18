"""Detect and extract tables from PDF pages via Camelot, with a pdfplumber fallback."""

from __future__ import annotations

from pathlib import Path
from typing import List


def extract_tables(pdf_path: Path, page_number: int) -> List[List[List[str]]]:
    """Return a list of tables for the given 1-based page number.

    Each table is a list of rows; each row is a list of cell strings.
    Tries Camelot first, falls back to pdfplumber, returns [] if both miss.
    """
    tables: List[List[List[str]]] = []

    # ---- Camelot ----
    try:
        import camelot  # type: ignore
    except ImportError:
        camelot = None  # type: ignore

    if camelot is not None:
        for flavor in ("lattice", "stream"):
            try:
                t = camelot.read_pdf(
                    str(pdf_path), pages=str(page_number), flavor=flavor
                )
            except Exception:
                continue
            for tbl in t:
                rows = [list(map(str, r)) for r in tbl.df.values.tolist()]
                # Camelot includes the header as the first row when flavor=lattice.
                if rows:
                    tables.append(rows)
            if tables:
                return tables

    # ---- pdfplumber fallback ----
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return tables

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            page = pdf.pages[page_number - 1]
            for raw in page.extract_tables() or []:
                rows = [[(c or "") for c in r] for r in raw]
                if rows:
                    tables.append(rows)
    except Exception:
        pass

    return tables
