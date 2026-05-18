"""Nougat backend: shell out to `nougat` and translate MMD → LaTeX blocks."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator, List, TYPE_CHECKING

from doc2latex.blocks import Block

if TYPE_CHECKING:
    from rich.console import Console

    from doc2latex.pipeline import ConvertOptions


class NougatReader:
    def read(
        self, opts: "ConvertOptions", console: "Console"
    ) -> Iterator[Block]:
        binary = shutil.which("nougat")
        if not binary:
            raise RuntimeError(
                "nougat binary not found on PATH. Install with: pip install nougat-ocr"
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cmd = [binary, str(opts.input), "-o", str(tmp_path), "--no-skipping"]
            if opts.verbose:
                console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
            try:
                subprocess.run(cmd, check=True, capture_output=not opts.verbose)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"nougat failed: {e}") from e

            mmd_files = list(tmp_path.glob("*.mmd"))
            if not mmd_files:
                raise RuntimeError("nougat produced no output (.mmd) file.")
            mmd_text = mmd_files[0].read_text(encoding="utf-8", errors="replace")

        yield from mmd_to_blocks(mmd_text)


# ---------------------------------------------------------------------------
# MMD / markdown → Block conversion. Intentionally small + forgiving.
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_OL_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
_UL_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_INLINE_MATH_RE = re.compile(r"\\\((.+?)\\\)")
_DISPLAY_MATH_RE = re.compile(r"\\\[(.+?)\\\]", re.S)


def mmd_to_blocks(text: str) -> Iterator[Block]:
    """Convert Nougat MMD output to Block objects."""
    # Split on display equations first so they survive line-based parsing.
    parts: List[tuple[str, str]] = []
    pos = 0
    for m in _DISPLAY_MATH_RE.finditer(text):
        if m.start() > pos:
            parts.append(("text", text[pos:m.start()]))
        parts.append(("eq", m.group(1).strip()))
        pos = m.end()
    if pos < len(text):
        parts.append(("text", text[pos:]))

    for kind, payload in parts:
        if kind == "eq":
            yield Block(kind="equation", content=payload, display=True)
            continue
        yield from _text_part_to_blocks(payload)


def _text_part_to_blocks(text: str) -> Iterator[Block]:
    lines = text.splitlines()
    para_buf: List[str] = []
    list_buf: List[str] = []
    list_ordered = False
    in_list = False

    def emit_para():
        nonlocal para_buf
        if not para_buf:
            return None
        joined = " ".join(s.strip() for s in para_buf).strip()
        para_buf = []
        if not joined:
            return None
        # \(x\) → $x$
        joined = _INLINE_MATH_RE.sub(lambda m: f"${m.group(1)}$", joined)
        # strip embedded image refs — those become separate figure blocks
        joined = _IMG_RE.sub("", joined).strip()
        if not joined:
            return None
        return Block(kind="para", content=joined)

    def emit_list():
        nonlocal list_buf, in_list, list_ordered
        if not list_buf:
            return None
        blk = Block(kind="list", ordered=list_ordered, items=list_buf)
        list_buf = []
        in_list = False
        list_ordered = False
        return blk

    for line in lines:
        stripped = line.strip()
        if not stripped:
            p = emit_para()
            if p:
                yield p
            ll = emit_list()
            if ll:
                yield ll
            continue

        mh = _HEADING_RE.match(stripped)
        if mh:
            p = emit_para()
            if p:
                yield p
            ll = emit_list()
            if ll:
                yield ll
            yield Block(kind="heading", content=mh.group(2), level=len(mh.group(1)))
            continue

        mo = _OL_ITEM_RE.match(stripped)
        mu = _UL_ITEM_RE.match(stripped)
        if mo or mu:
            p = emit_para()
            if p:
                yield p
            ordered_now = bool(mo)
            if in_list and ordered_now != list_ordered:
                ll = emit_list()
                if ll:
                    yield ll
            in_list = True
            list_ordered = ordered_now
            list_buf.append((mo or mu).group(1))
            continue

        mi = _IMG_RE.match(stripped)
        if mi:
            p = emit_para()
            if p:
                yield p
            ll = emit_list()
            if ll:
                yield ll
            yield Block(kind="figure", content=mi.group(2), caption=mi.group(1) or None)
            continue

        para_buf.append(stripped)

    p = emit_para()
    if p:
        yield p
    ll = emit_list()
    if ll:
        yield ll
