"""Dispatch input files to the appropriate reader."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from doc2latex.blocks import Block
    from doc2latex.pipeline import ConvertOptions


class Reader(Protocol):
    def read(
        self, opts: "ConvertOptions", console: "Console"
    ) -> Iterable["Block"]:  # pragma: no cover - protocol
        ...


_PDF_EXT = {".pdf"}
_DOCX_EXT = {".docx"}
_IMAGE_EXT = {".jpg", ".jpeg", ".png"}


def route(path: Path, backend: str = "basic") -> Reader:
    """Pick a reader based on the file extension and backend flag."""
    ext = path.suffix.lower()

    if ext in _PDF_EXT:
        if backend == "nougat":
            from doc2latex.readers.nougat_reader import NougatReader

            return NougatReader()
        if backend == "marker":
            from doc2latex.readers.marker_reader import MarkerReader

            return MarkerReader()
        from doc2latex.readers.pdf_reader import PdfReader

        return PdfReader()

    if ext in _DOCX_EXT:
        from doc2latex.readers.docx_reader import DocxReader

        return DocxReader()

    if ext in _IMAGE_EXT:
        from doc2latex.readers.image_reader import ImageReader

        return ImageReader()

    raise ValueError(
        f"unsupported file extension: {ext!r}. "
        f"supported: .pdf, .docx, .jpg, .jpeg, .png"
    )
