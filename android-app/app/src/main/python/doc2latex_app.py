"""Bridge module between Chaquopy (Android) and the doc2latex package.

Chaquopy can't drive Typer/Rich cleanly, so we expose a single callable that
runs the pipeline with sane defaults and returns a JSON string.

Note: the heavy ML backends (pix2tex, nougat, marker, opencv, camelot) are
intentionally NOT installed in the Android app — they don't fit and don't
build for ARM. Only DOCX / native-PDF / pdfplumber-table paths work here.
"""

from __future__ import annotations

import json
from pathlib import Path


def convert(input_path: str, out_path: str, assets_dir: str) -> str:
    """Run a basic conversion. Returns a JSON string with output paths."""
    from doc2latex.pipeline import ConvertOptions, run_conversion

    opts = ConvertOptions(
        input=Path(input_path),
        out=Path(out_path),
        assets_dir=Path(assets_dir),
        backend="basic",
        no_equations=True,   # pix2tex isn't available on Android
        no_tables=False,     # pdfplumber tables work
        verbose=False,
    )
    result = run_conversion(opts)
    return json.dumps({
        "out_path": str(result.out_path),
        "assets_dir": str(result.assets_dir),
        "block_count": result.block_count,
        "asset_count": result.asset_count,
    })
