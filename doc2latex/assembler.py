"""Stitch a list of Block objects into a single LaTeX document."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from doc2latex.blocks import Block
from doc2latex.converters import table_to_latex, text_to_latex


def _render_block(block: Block, assets_dir_name: str = "assets") -> str:
    """Render a single block as a LaTeX fragment."""
    kind = block.kind

    if kind == "heading":
        return text_to_latex.heading(block.content, block.level or 1)

    if kind == "para":
        return text_to_latex.paragraph(block.content)

    if kind == "equation":
        latex = block.content.strip()
        if block.display:
            # Use equation* to avoid auto-numbering surprises in tests.
            return f"\\begin{{equation*}}\n{latex}\n\\end{{equation*}}"
        return f"${latex}$"

    if kind == "figure":
        # `content` is a path to the asset (relative or absolute).
        path = Path(block.content)
        # Always reference by `<assets_dir_name>/<basename>` in the .tex so the
        # output is portable.
        ref = f"{assets_dir_name}/{path.name}" if path.name else block.content
        caption = block.caption
        lines = [
            r"\begin{figure}[h]",
            r"  \centering",
            f"  \\includegraphics[width=0.8\\linewidth]{{{ref}}}",
        ]
        if caption:
            lines.append(f"  \\caption{{{text_to_latex.escape(caption)}}}")
        lines.append(r"\end{figure}")
        return "\n".join(lines)

    if kind == "table":
        return table_to_latex.render(block.rows, caption=block.caption)

    if kind == "list":
        env = "enumerate" if block.ordered else "itemize"
        items = block.items or ([block.content] if block.content else [])
        body = "\n".join(f"  \\item {text_to_latex.escape(it)}" for it in items)
        return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

    # Unknown block kinds become escaped paragraphs so we never emit junk.
    return text_to_latex.escape(block.content)


def _get_env() -> Environment:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        # We are emitting LaTeX, NOT HTML. Disable autoescape but keep the
        # interface consistent.
        autoescape=select_autoescape(disabled_extensions=("jinja",), default=False),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    return env


def assemble(
    blocks: Iterable[Block],
    title: str = "",
    author: str = "",
    assets_dir_name: str = "assets",
) -> str:
    """Render the full LaTeX document as a string."""
    env = _get_env()
    template = env.get_template("base.tex.jinja")
    rendered = [_render_block(b, assets_dir_name=assets_dir_name) for b in blocks]
    return template.render(
        title=text_to_latex.escape(title),
        author=text_to_latex.escape(author),
        rendered_blocks=rendered,
    )
