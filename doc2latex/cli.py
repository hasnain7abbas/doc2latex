"""Typer-based CLI entry point for doc2latex."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from doc2latex import __version__

app = typer.Typer(
    name="doc2latex",
    help="Offline PDF / DOCX / image to LaTeX converter.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

# Set by the top-level --emit-json flag. When True, the convert command
# prints a JSON object on stdout as its last line — used by the Tauri shell.
_emit_json: bool = False


class Backend(str, Enum):
    basic = "basic"
    nougat = "nougat"
    marker = "marker"


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"doc2latex {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    emit_json: bool = typer.Option(
        False,
        "--emit-json",
        help="Emit a single JSON result object on stdout (for tooling).",
    ),
) -> None:
    """doc2latex CLI."""
    global _emit_json
    _emit_json = emit_json


@app.command()
def convert(
    input: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Input file (.pdf, .docx, .jpg, .jpeg, .png).",
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="Output .tex path. Defaults to <input>.tex."
    ),
    assets_dir: Optional[Path] = typer.Option(
        None,
        "--assets-dir",
        help="Directory for extracted assets. Defaults to <out>_assets.",
    ),
    backend: Backend = typer.Option(
        Backend.basic, "--backend", help="Conversion backend."
    ),
    ocr_lang: str = typer.Option(
        "eng", "--ocr-lang", help="Tesseract language(s), e.g. 'eng' or 'eng+deu'."
    ),
    dpi: int = typer.Option(
        300, "--dpi", min=72, max=1200, help="Rasterization DPI for image OCR paths."
    ),
    no_equations: bool = typer.Option(
        False, "--no-equations", help="Skip equation detection / OCR."
    ),
    no_tables: bool = typer.Option(
        False, "--no-tables", help="Skip table detection."
    ),
    whole_equation: bool = typer.Option(
        False,
        "--whole-equation",
        help="For image inputs, treat the entire image as one equation.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """Convert <input> to LaTeX."""
    # Local import keeps `--help` fast and avoids importing heavy deps unnecessarily.
    from doc2latex.pipeline import ConvertOptions, run_conversion

    out_path = out or input.with_suffix(".tex")
    assets_path = assets_dir or out_path.with_name(out_path.stem + "_assets")

    opts = ConvertOptions(
        input=input,
        out=out_path,
        assets_dir=assets_path,
        backend=backend.value,
        ocr_lang=ocr_lang,
        dpi=dpi,
        no_equations=no_equations,
        no_tables=no_tables,
        whole_equation=whole_equation,
        verbose=verbose,
    )

    try:
        result = run_conversion(opts, console=console, err_console=err_console)
    except FileNotFoundError as e:
        err_console.print(f"[red]bad input:[/red] {e}")
        raise typer.Exit(code=2)
    except RuntimeError as e:
        # Distinguish missing-system-dep messages by convention.
        msg = str(e)
        if "not found" in msg.lower() or "missing" in msg.lower():
            err_console.print(f"[red]missing system dependency:[/red] {msg}")
            raise typer.Exit(code=3)
        err_console.print(f"[red]conversion failure:[/red] {msg}")
        raise typer.Exit(code=4)

    if _emit_json:
        import json
        payload = {
            "out_path": str(result.out_path),
            "assets_dir": str(result.assets_dir),
            "block_count": result.block_count,
            "asset_count": result.asset_count,
        }
        # Plain print (not rich.console) so the JSON is the only content on
        # the line — easy to parse from the shell side.
        print(json.dumps(payload))
    else:
        console.print(
            f"[green]wrote[/green] {result.out_path}  "
            f"([dim]{result.block_count} blocks, "
            f"{result.asset_count} assets[/dim])"
        )


if __name__ == "__main__":  # pragma: no cover
    app()
