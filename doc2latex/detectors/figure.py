"""Figure / image bounding-box helpers."""

from __future__ import annotations

from typing import Optional, Tuple


def find_caption(
    text_blocks: list[dict],
    image_bbox: Tuple[float, float, float, float],
    max_gap: float = 50.0,
) -> Optional[str]:
    """Return the caption text immediately below `image_bbox`, if any."""
    if not text_blocks:
        return None
    img_bottom = image_bbox[3]
    img_left, img_right = image_bbox[0], image_bbox[2]

    candidates = []
    for tb in text_blocks:
        bx0, by0, bx1, by1 = tb["bbox"]
        if by0 < img_bottom:
            continue
        if by0 - img_bottom > max_gap:
            continue
        # Horizontal overlap check.
        if bx1 < img_left or bx0 > img_right:
            continue
        text = tb["text"].strip()
        if not text:
            continue
        if text.lower().startswith(("figure", "fig.", "table", "tab.")):
            candidates.append((by0 - img_bottom, text))

    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1].split("\n", 1)[0]
