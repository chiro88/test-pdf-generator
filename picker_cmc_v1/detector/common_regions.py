"""Common-region (header/footer/watermark) detection (D13 + D16).

Headers/footers are BANDS: a single header/footer per page expands to the full
content-margin band; a multi-part footer (left/center/right fragments at the
same y, not x-overlapping) is emitted as separate fragment bands so it matches
the truth's per-fragment regions. Watermark detection is restricted to standalone
watermark text (exact CONFIDENTIAL/DRAFT or 'Licensed to ...'), so a
"Confidential — Page N" footer is NOT mistaken for a watermark, and a near-footer
watermark is not mistaken for a footer. Rotated/morph/image-like watermarks
remain a reported limitation (never silently skipped).
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from .models import PageExtract

MARGIN = 86.0
_COMMON_MARGIN = 48.0
_TOP_BAND = 80.0
_BOT_BAND = 80.0
_BAND_BASE = 35.0
_BAND_PER_LINE = 6.0
_MERGE_GAP = 4.0
_FRAGMENT_PAD = 3.0

# Standalone watermark text (exact CONFIDENTIAL/DRAFT, or a licence line). The
# exact anchors keep a "Confidential — Page 1" footer from matching.
_WM_RE = re.compile(r"^(CONFIDENTIAL|DRAFT)$|^Licensed to\b")
_WM_BAND_PAD = 18.0


def body_zone(height: float) -> tuple[float, float]:
    return (MARGIN, height - MARGIN)


def _norm(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", (text or "").strip().lower()))


def _is_watermark(text: str) -> bool:
    return _WM_RE.match((text or "").strip()) is not None


def _merge_lines(lines: List) -> List[List]:
    """Merge vertically-stacked, x-overlapping margin lines into multi-line blocks.
    Side-by-side fragments (same y, no x-overlap) are NOT merged."""
    lines = sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))
    blocks: List[List] = []
    for ln in lines:
        placed = False
        for blk in blocks:
            last = blk[-1]
            if (ln.bbox[1] - last.bbox[3]) < _MERGE_GAP and not (ln.bbox[2] <= last.bbox[0] or ln.bbox[0] >= last.bbox[2]):
                blk.append(ln)
                placed = True
                break
        if not placed:
            blocks.append([ln])
    return blocks


def _band(block: List, kind: str, page_w: float, region_id: str, full_width: bool) -> dict:
    text = "\n".join(l.text for l in block)
    top = min(l.bbox[1] for l in block)
    height = _BAND_BASE + _BAND_PER_LINE * (len(block) - 1)
    if full_width:
        x0, x1 = _COMMON_MARGIN, page_w - _COMMON_MARGIN
    else:
        x0 = max(0.0, min(l.bbox[0] for l in block) - _FRAGMENT_PAD)
        x1 = min(page_w, max(l.bbox[2] for l in block) + _FRAGMENT_PAD)
    return {"kind": kind, "bbox": [round(x0, 2), round(top, 2), round(x1, 2), round(top + height, 2)],
            "text": text, "common_region_id": region_id}


def detect_common_regions(pages: List[PageExtract]) -> List[List[dict]]:
    out: List[List[dict]] = [[] for _ in pages]
    norm_to_id: Dict[str, str] = {}
    hdr_n = ftr_n = wm_n = 0

    for pi, p in enumerate(pages):
        h = p.height
        top_lines = [ln for ln in p.lines if ln.bbox[1] < _TOP_BAND and not _is_watermark(ln.text)]
        bot_lines = [ln for ln in p.lines if ln.bbox[3] > h - _BOT_BAND and not _is_watermark(ln.text)]

        for kind, lines in (("header", top_lines), ("footer", bot_lines)):
            blocks = _merge_lines(lines)
            full_width = len(blocks) <= 1   # single header/footer -> full band; multipart -> per-fragment
            for block in blocks:
                key = kind + "|" + "|".join(_norm(l.text) for l in block)
                if key not in norm_to_id:
                    if kind == "header":
                        hdr_n += 1
                        norm_to_id[key] = f"hdr_{hdr_n:03d}"
                    else:
                        ftr_n += 1
                        norm_to_id[key] = f"ftr_{ftr_n:03d}"
                out[pi].append(_band(block, kind, p.width, norm_to_id[key], full_width))

        # Extractable watermark text (standalone), expanded into a band.
        for ln in p.lines:
            if _is_watermark(ln.text):
                key = "wm|" + _norm(ln.text)
                if key not in norm_to_id:
                    wm_n += 1
                    norm_to_id[key] = f"wm_{wm_n:03d}"
                b = ln.bbox
                out[pi].append({"kind": "watermark",
                                "bbox": [max(0.0, b[0] - _WM_BAND_PAD), max(0.0, b[1] - _WM_BAND_PAD),
                                         min(p.width, b[2] + _WM_BAND_PAD), min(p.height, b[3] + _WM_BAND_PAD)],
                                "text": ln.text, "common_region_id": norm_to_id[key]})
    return out
