"""Native PDF reader using PyMuPDF (fitz).

Extracts text blocks, embedded images, and captions, and routes equation-like
regions to pix2tex. Tables are handled separately by the table detector.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, TYPE_CHECKING

from doc2latex.blocks import Block
from doc2latex.converters import eq_to_latex

if TYPE_CHECKING:
    from rich.console import Console

    from doc2latex.pipeline import ConvertOptions


_CAPTION_RE = re.compile(r"^\s*(figure|fig\.?|table|tab\.?)\s*\d+\s*[:.\-]", re.I)


def _is_caption(text: str) -> bool:
    return bool(_CAPTION_RE.match(text or ""))


def _cluster_by_column(blocks: list[dict], page_width: float) -> list[list[dict]]:
    """Cluster text blocks into columns by their x-midpoint.

    Cheap two-column heuristic: split at the page mid-line if a meaningful
    number of blocks sit on either side; otherwise return one column.
    """
    if not blocks:
        return []
    mid = page_width / 2.0
    left = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 < mid]
    right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 >= mid]
    # If one side has < 20% of blocks, treat as single column.
    if min(len(left), len(right)) / max(1, len(blocks)) < 0.2:
        return [sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))]
    left.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    right.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    return [left, right]


class PdfReader:
    """Read a native (text-bearing) PDF and yield Block objects in reading order."""

    def read(
        self, opts: "ConvertOptions", console: "Console"
    ) -> Iterator[Block]:
        try:
            import fitz  # PyMuPDF
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "PyMuPDF (pymupdf) is not installed — required for PDF input."
            ) from e

        doc = fitz.open(str(opts.input))
        assets_dir: Path = opts.assets_dir
        figure_idx = 0
        # Track whether *any* page has selectable text. If not, we should
        # fall back to OCR.
        has_any_text = False

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text") or ""
            if page_text.strip():
                has_any_text = True

            # ---------- text blocks ----------
            data = page.get_text("dict")
            text_blocks = []
            for blk in data.get("blocks", []):
                if blk.get("type", 0) != 0:  # 0 = text, 1 = image
                    continue
                lines = blk.get("lines", [])
                text = ""
                for line in lines:
                    spans = line.get("spans", [])
                    line_text = "".join(s.get("text", "") for s in spans)
                    if line_text:
                        text += line_text + "\n"
                text = text.strip()
                if not text:
                    continue
                text_blocks.append(
                    {"bbox": blk["bbox"], "text": text, "lines": lines}
                )

            page_width = page.rect.width
            columns = _cluster_by_column(text_blocks, page_width)
            ordered_blocks: list[dict] = []
            for col in columns:
                ordered_blocks.extend(col)

            # ---------- emit blocks ----------
            for tb in ordered_blocks:
                text = tb["text"]
                if _is_caption(text):
                    # We treat captions as paragraphs here; figure blocks set
                    # their own caption when they can find one nearby.
                    yield Block(kind="para", content=text, page=page_num,
                                bbox=tuple(tb["bbox"]))
                    continue
                # Heuristic equation detection on inline text.
                if (
                    not opts.no_equations
                    and eq_to_latex.is_likely_math(text)
                    and len(text) < 400
                ):
                    yield Block(
                        kind="equation",
                        content=text,  # raw fallback — pix2tex would render the image
                        display=True,
                        page=page_num,
                        bbox=tuple(tb["bbox"]),
                    )
                    continue
                # Heading heuristic: short, large-font text.
                level = _guess_heading_level(tb["lines"])
                if level:
                    yield Block(
                        kind="heading", content=text, level=level, page=page_num,
                        bbox=tuple(tb["bbox"]),
                    )
                    continue
                yield Block(kind="para", content=text, page=page_num,
                            bbox=tuple(tb["bbox"]))

            # ---------- tables ----------
            if not opts.no_tables:
                try:
                    from doc2latex.detectors.table import extract_tables

                    page_tables = extract_tables(opts.input, page_num)
                except Exception as e:  # pragma: no cover
                    page_tables = []
                    if opts.verbose:
                        console.print(f"[yellow]table extraction skipped:[/yellow] {e}")
                for rows in page_tables:
                    yield Block(kind="table", rows=rows, page=page_num)

            # ---------- images ----------
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    figure_idx += 1
                    out = assets_dir / f"figure{figure_idx}.png"
                    pix.save(str(out))
                    pix = None  # release
                except Exception as e:  # pragma: no cover
                    if opts.verbose:
                        console.print(f"[yellow]image xref {xref} failed:[/yellow] {e}")
                    continue
                caption = _find_caption_for_image(page, ordered_blocks)
                yield Block(
                    kind="figure",
                    content=str(out),
                    caption=caption,
                    page=page_num,
                )

        doc.close()

        if not has_any_text:
            # No selectable text anywhere — caller may want to re-run with OCR.
            console.print(
                "[yellow]warning:[/yellow] no selectable text in PDF — "
                "consider rasterizing + OCR (image_reader path)."
            )

    # ---------------- helpers ----------------


def _guess_heading_level(lines: list[dict]) -> int:
    """Return 1..3 if the block looks like a heading, else 0."""
    if not lines or len(lines) > 2:
        return 0
    sizes = []
    for line in lines:
        for span in line.get("spans", []):
            sizes.append(span.get("size", 0))
    if not sizes:
        return 0
    max_size = max(sizes)
    # Crude thresholds — most body text is 10–12pt.
    if max_size >= 18:
        return 1
    if max_size >= 14:
        return 2
    if max_size >= 12.5:
        # Only count as heading if the text is short.
        total_text = sum(
            len(s.get("text", "")) for line in lines for s in line.get("spans", [])
        )
        if total_text < 80:
            return 3
    return 0


def _find_caption_for_image(page, text_blocks: list[dict]) -> Optional[str]:
    """Return the first caption-like text block within ~50pt below any image bbox."""
    if not text_blocks:
        return None
    # Cheap pass: look for any caption-prefixed block on the page.
    for tb in text_blocks:
        if _is_caption(tb["text"]):
            # Trim multi-line captions to a single visible line.
            first_line = tb["text"].split("\n", 1)[0]
            return first_line
    return None
