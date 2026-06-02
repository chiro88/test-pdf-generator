"""Caption/title anchor detection over extracted text lines (D11)."""
from __future__ import annotations

from typing import List

from .models import Anchor, PageExtract
from .title_patterns import match_caption


def find_anchors(extract: PageExtract) -> List[Anchor]:
    anchors: List[Anchor] = []
    for line in extract.lines:
        m = match_caption(line.text)
        if m:
            kind, index, title = m
            anchors.append(Anchor(kind=kind, index=index, title=title, caption_bbox=list(line.bbox)))
    anchors.sort(key=lambda a: a.caption_bbox[1])
    return anchors
