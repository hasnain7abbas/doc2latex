"""Marker backend: shell out to `marker_single` and translate its markdown output."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator, TYPE_CHECKING

from doc2latex.blocks import Block
from doc2latex.readers.nougat_reader import mmd_to_blocks

if TYPE_CHECKING:
    from rich.console import Console

    from doc2latex.pipeline import ConvertOptions


class MarkerReader:
    def read(
        self, opts: "ConvertOptions", console: "Console"
    ) -> Iterator[Block]:
        binary = shutil.which("marker_single")
        if not binary:
            raise RuntimeError(
                "marker_single binary not found on PATH. "
                "Install with: pip install marker-pdf"
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cmd = [binary, str(opts.input), str(tmp_path)]
            if opts.verbose:
                console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
            try:
                subprocess.run(cmd, check=True, capture_output=not opts.verbose)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"marker failed: {e}") from e

            md_files = list(tmp_path.rglob("*.md"))
            if not md_files:
                raise RuntimeError("marker produced no markdown output.")
            md_text = md_files[0].read_text(encoding="utf-8", errors="replace")

            # Marker also drops images in the same dir; copy them to assets.
            for img in tmp_path.rglob("*"):
                if img.is_file() and img.suffix.lower() in {
                    ".png", ".jpg", ".jpeg",
                }:
                    target = opts.assets_dir / img.name
                    target.write_bytes(img.read_bytes())

        # Marker emits markdown with $$...$$ for display math — convert those to
        # the \[...\] form mmd_to_blocks expects.
        md_text = _normalize_marker_math(md_text)
        yield from mmd_to_blocks(md_text)


def _normalize_marker_math(text: str) -> str:
    """Convert $$...$$ → \\[ ... \\], $...$ → \\( ... \\)."""
    import re

    text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: "\\[" + m.group(1) + "\\]",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"(?<!\$)\$([^\$\n]+?)\$(?!\$)",
        lambda m: "\\(" + m.group(1) + "\\)",
        text,
    )
    return text
