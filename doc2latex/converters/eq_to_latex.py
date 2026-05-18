"""Wrapper around pix2tex for equation image → LaTeX."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# pix2tex is heavy (PyTorch). Load it lazily through a singleton so multiple
# equations on the same run share one model instance.
_MODEL = None


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        from pix2tex.cli import LatexOCR  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pix2tex is not installed. Install with: pip install 'doc2latex[ocr]'"
        ) from e
    _MODEL = LatexOCR()
    return _MODEL


def image_to_latex(image_path: Path | str) -> str:
    """Run pix2tex on the given image and return raw LaTeX (no $ delimiters)."""
    from PIL import Image

    model = _load_model()
    img = Image.open(str(image_path))
    return model(img).strip()


def pil_to_latex(image) -> str:
    """Run pix2tex on a PIL image."""
    model = _load_model()
    return model(image).strip()


def wrap(latex: str, display: bool = True) -> str:
    """Wrap raw LaTeX in display or inline math delimiters."""
    latex = latex.strip()
    if display:
        return f"\\begin{{equation*}}\n{latex}\n\\end{{equation*}}"
    return f"${latex}$"


def is_likely_math(text: str, threshold: float = 0.3) -> bool:
    """Quick heuristic: does this text look like math (many non-ASCII math glyphs)?"""
    if not text:
        return False
    math_chars = set("∑∫∏√∞≤≥≠≈±×÷⋅·⟨⟩∂∇αβγδεζηθικλμνξπρσςτυφχψωΑΒΓΔΘΛΞΠΣΦΨΩℝℕℤℚℂ")
    hits = sum(1 for c in text if c in math_chars)
    return hits / max(1, len(text)) >= threshold


__all__ = ["image_to_latex", "pil_to_latex", "wrap", "is_likely_math"]


# Optional context manager to release the model (for tests / long-running daemons).
def reset_model() -> None:  # pragma: no cover
    global _MODEL
    _MODEL = None


# Allow forward-ref of Optional for type checkers
_ = Optional
