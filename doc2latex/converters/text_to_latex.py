"""Escape and structurally map plain text → LaTeX."""

from __future__ import annotations

# Single-pass char map. Done in one pass so we never re-escape characters that
# appear inside our own replacement strings (e.g. the {} in \textbackslash{}).
_CHAR_MAP: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}


def escape(text: str) -> str:
    """Escape LaTeX special characters in plain text."""
    if not text:
        return ""
    return "".join(_CHAR_MAP.get(c, c) for c in text)


def heading(text: str, level: int) -> str:
    """Map a heading level (1-based) to a LaTeX sectioning command."""
    commands = [
        r"\section",
        r"\subsection",
        r"\subsubsection",
        r"\paragraph",
        r"\subparagraph",
    ]
    idx = max(0, min(len(commands) - 1, level - 1))
    return f"{commands[idx]}{{{escape(text)}}}"


def paragraph(text: str) -> str:
    return escape(text)
