"""Orchestrates the full conversion: input → blocks → LaTeX."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console

from doc2latex.assembler import assemble
from doc2latex.blocks import Block
from doc2latex.routers import route


@dataclass
class ConvertOptions:
    input: Path
    out: Path
    assets_dir: Path
    backend: str = "basic"
    ocr_lang: str = "eng"
    dpi: int = 300
    no_equations: bool = False
    no_tables: bool = False
    whole_equation: bool = False
    verbose: bool = False


@dataclass
class ConvertResult:
    out_path: Path
    assets_dir: Path
    block_count: int
    asset_count: int


def run_conversion(
    opts: ConvertOptions,
    console: Optional[Console] = None,
    err_console: Optional[Console] = None,
) -> ConvertResult:
    """Run the full pipeline. Returns a ConvertResult on success."""
    console = console or Console()
    err_console = err_console or Console(stderr=True)

    if not opts.input.exists():
        raise FileNotFoundError(opts.input)

    opts.assets_dir.mkdir(parents=True, exist_ok=True)
    opts.out.parent.mkdir(parents=True, exist_ok=True)

    if opts.verbose:
        console.print(f"[cyan]input:[/cyan] {opts.input}")
        console.print(f"[cyan]backend:[/cyan] {opts.backend}")

    reader = route(opts.input, backend=opts.backend)

    blocks: list[Block] = []
    from rich.progress import Progress, SpinnerColumn, TextColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
        disable=not opts.verbose,
    ) as progress:
        task = progress.add_task(f"reading {opts.input.name}", total=None)
        for blk in reader.read(opts, console=console):
            blocks.append(blk)
            progress.update(task, description=f"reading {opts.input.name} ({len(blocks)} blocks)")

    title = opts.input.stem.replace("_", " ")
    tex = assemble(
        blocks,
        title=title,
        author="",
        assets_dir_name=opts.assets_dir.name,
    )

    opts.out.write_text(tex, encoding="utf-8")

    asset_count = sum(1 for _ in opts.assets_dir.iterdir()) if opts.assets_dir.exists() else 0
    return ConvertResult(
        out_path=opts.out,
        assets_dir=opts.assets_dir,
        block_count=len(blocks),
        asset_count=asset_count,
    )
