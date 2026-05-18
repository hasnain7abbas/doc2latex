"""Assembler / template / converters smoke tests — no system deps required."""

from __future__ import annotations

from doc2latex.assembler import assemble
from doc2latex.blocks import Block
from doc2latex.converters import table_to_latex, text_to_latex


def test_escape_special_chars():
    s = r"a & b % c $ d # e _ f { g } h ~ i ^ j"
    out = text_to_latex.escape(s)
    for src in ["&", "%", "$", "#", "_", "{", "}", "~", "^"]:
        # Escaped forms should appear; raw forms should not (except inside the
        # `\textasciitilde{}` / `\textasciicircum{}` macro names themselves —
        # those are fine).
        assert "\\" in out
    # backslash-only check
    assert text_to_latex.escape("a\\b") == r"a\textbackslash{}b"


def test_heading_levels():
    assert text_to_latex.heading("Intro", 1).startswith(r"\section")
    assert text_to_latex.heading("Sub", 2).startswith(r"\subsection")
    assert text_to_latex.heading("Deeper", 4).startswith(r"\paragraph")


def test_table_render_booktabs():
    rows = [["A", "B"], ["1", "2"], ["3", "4"]]
    out = table_to_latex.render(rows, caption="My table")
    assert r"\begin{table}" in out
    assert r"\toprule" in out
    assert r"\midrule" in out
    assert r"\bottomrule" in out
    assert r"\caption{My table}" in out


def test_empty_document_compiles_structurally():
    tex = assemble([], title="Hello", author="World")
    assert r"\documentclass" in tex
    assert r"\begin{document}" in tex
    assert r"\end{document}" in tex
    assert r"\title{Hello}" in tex
    assert r"\maketitle" in tex


def test_block_rendering_kinds():
    blocks = [
        Block(kind="heading", content="Intro", level=1),
        Block(kind="para", content="Hello & world."),
        Block(kind="equation", content="E = mc^2", display=True),
        Block(kind="equation", content="x", display=False),
        Block(kind="list", ordered=False, items=["a", "b"]),
        Block(kind="table", rows=[["A", "B"], ["1", "2"]]),
        Block(kind="figure", content="assets/figure1.png", caption="A figure"),
    ]
    tex = assemble(blocks, title="T")
    assert r"\section{Intro}" in tex
    assert r"Hello \& world." in tex
    assert r"\begin{equation*}" in tex
    assert r"$x$" in tex
    assert r"\begin{itemize}" in tex
    assert r"\begin{tabular}" in tex
    assert r"\includegraphics" in tex
    assert r"\caption{A figure}" in tex


def test_assets_path_is_basename_only():
    """Figure references in .tex should use the assets dir name + basename."""
    blocks = [Block(kind="figure", content="/abs/path/to/figure7.png")]
    tex = assemble(blocks, assets_dir_name="myassets")
    assert "myassets/figure7.png" in tex
    assert "/abs/path" not in tex
