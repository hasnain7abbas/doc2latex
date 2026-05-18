"""Block dataclass — the normalized intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple

BlockKind = Literal[
    "heading",
    "para",
    "equation",
    "figure",
    "table",
    "list",
]


@dataclass
class Block:
    kind: BlockKind
    content: str = ""
    level: int = 0
    caption: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    page: Optional[int] = None
    # Block-specific extras.
    display: bool = True            # equations: True => display, False => inline
    ordered: bool = False           # lists: True => enumerate, False => itemize
    items: list[str] = field(default_factory=list)  # list block items
    rows: list[list[str]] = field(default_factory=list)  # table rows (raw text)

    def is_inline_equation(self) -> bool:
        return self.kind == "equation" and not self.display
