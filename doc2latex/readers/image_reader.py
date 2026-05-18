"""JPEG / PNG reader: Tesseract for text, pix2tex for equations."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, TYPE_CHECKING

from doc2latex.blocks import Block

if TYPE_CHECKING:
    from rich.console import Console

    from doc2latex.pipeline import ConvertOptions


class ImageReader:
    def read(
        self, opts: "ConvertOptions", console: "Console"
    ) -> Iterator[Block]:
        path: Path = opts.input

        # Copy the source image into the assets directory so the .tex is
        # self-contained.
        asset_path = opts.assets_dir / path.name
        asset_path.write_bytes(path.read_bytes())

        # --whole-equation: skip OCR entirely, emit one equation block.
        if opts.whole_equation:
            if opts.no_equations:
                yield Block(kind="figure", content=str(asset_path),
                            caption=path.stem)
                return
            try:
                from doc2latex.converters.eq_to_latex import image_to_latex
            except RuntimeError:
                raise
            latex = image_to_latex(asset_path)
            yield Block(kind="equation", content=latex, display=True)
            return

        # ---- OCR text path ----
        try:
            import pytesseract  # type: ignore
            from PIL import Image
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "pytesseract / Pillow not installed — install with "
                "'pip install doc2latex[ocr]' and the tesseract binary."
            ) from e

        try:
            img = Image.open(str(asset_path))
            text = pytesseract.image_to_string(img, lang=opts.ocr_lang)
        except pytesseract.TesseractNotFoundError as e:  # type: ignore[attr-defined]
            raise RuntimeError("tesseract binary not found on PATH.") from e
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"OCR failed: {e}") from e

        text = (text or "").strip()
        if text:
            # Emit each non-empty paragraph as its own para block.
            for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
                yield Block(kind="para", content=para)

        # Always also include the original image as a figure for reference.
        yield Block(kind="figure", content=str(asset_path), caption=path.stem)
