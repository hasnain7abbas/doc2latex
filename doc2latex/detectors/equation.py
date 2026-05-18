"""Equation region detection helpers for the basic PDF path.

The Nougat / Marker backends do their own layout detection — these helpers are
only used by the per-block pipeline for native PDFs and rasterized images.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

_MATH_GLYPHS = set(
    "∑∫∏√∞≤≥≠≈±×÷⋅·⟨⟩∂∇αβγδεζηθικλμνξπρσςτυφχψω"
    "ΑΒΓΔΘΛΞΠΣΦΨΩℝℕℤℚℂ"
)


def math_glyph_density(text: str) -> float:
    """Fraction of characters that are non-ASCII math glyphs."""
    if not text:
        return 0.0
    return sum(1 for c in text if c in _MATH_GLYPHS) / len(text)


def is_equation_text(text: str, threshold: float = 0.3) -> bool:
    return math_glyph_density(text) >= threshold


def merge_bboxes(bboxes: Iterable[Tuple[float, float, float, float]]):
    """Return the bounding box that contains all inputs (or None)."""
    bboxes = list(bboxes)
    if not bboxes:
        return None
    x0 = min(b[0] for b in bboxes)
    y0 = min(b[1] for b in bboxes)
    x1 = max(b[2] for b in bboxes)
    y1 = max(b[3] for b in bboxes)
    return (x0, y0, x1, y1)
