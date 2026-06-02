"""Common-region (header/footer) detection hook + body-zone masking (D11).

This is a hook, not a full common-region detector. It finds top/bottom text
lines that repeat across pages (digit-insensitive, to catch variable page
numbers / subtitles) and exposes a body zone so figure/table inference excludes
the header/footer margins.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from .models import PageExtract

MARGIN = 86.0
_TOP_BAND = 80.0
_BOT_BAND = 80.0


def body_zone(height: float) -> tuple[float, float]:
    return (MARGIN, height - MARGIN)


def _norm(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", (text or "").strip().lower()))


def detect_common_regions(pages: List[PageExtract]) -> List[List[dict]]:
    """Return per-page list of {kind, bbox, text} header/footer candidates."""
    n = len(pages)
    out: List[List[dict]] = [[] for _ in pages]
    if n == 0:
        return out

    top: Dict[str, list] = defaultdict(list)
    bot: Dict[str, list] = defaultdict(list)
    for pi, p in enumerate(pages):
        h = p.height
        for ln in p.lines:
            if ln.bbox[1] < _TOP_BAND:
                top[_norm(ln.text)].append((pi, ln))
            elif ln.bbox[3] > h - _BOT_BAND:
                bot[_norm(ln.text)].append((pi, ln))

    threshold = max(2, (n + 1) // 2)  # repeated on at least half the pages

    def emit(groups: Dict[str, list], kind: str):
        for occ in groups.values():
            page_ids = {pi for pi, _ in occ}
            if n >= 2 and len(page_ids) >= threshold:
                for pi, ln in occ:
                    out[pi].append({"kind": kind, "bbox": list(ln.bbox), "text": ln.text})

    emit(top, "header")
    emit(bot, "footer")
    return out
