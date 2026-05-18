"""Render a 2D table of strings as a tabular environment with booktabs rules."""

from __future__ import annotations

from typing import Sequence

from doc2latex.converters.text_to_latex import escape


def render(
    rows: Sequence[Sequence[str]],
    caption: str | None = None,
    label: str | None = None,
) -> str:
    """Return a LaTeX table[...] block containing a booktabs tabular."""
    if not rows:
        return ""
    n_cols = max(len(r) for r in rows)
    col_spec = "l" * n_cols

    def fmt_row(row: Sequence[str]) -> str:
        cells = [escape(c) for c in row]
        # Pad missing cells so & alignment is preserved.
        cells += [""] * (n_cols - len(cells))
        return " & ".join(cells) + r" \\"

    header = fmt_row(rows[0])
    body = "\n".join(fmt_row(r) for r in rows[1:])

    lines = [
        r"\begin{table}[h]",
        r"  \centering",
    ]
    if caption:
        lines.append(f"  \\caption{{{escape(caption)}}}")
    if label:
        lines.append(f"  \\label{{{label}}}")
    lines.append(f"  \\begin{{tabular}}{{{col_spec}}}")
    lines.append(r"    \toprule")
    lines.append(f"    {header}")
    lines.append(r"    \midrule")
    if body:
        for line in body.split("\n"):
            lines.append(f"    {line}")
    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)
