"""Common-region (header/footer/watermark) band detection (D13).

Headers/footers are emitted as BANDS (content-margin x-range, merged multiline
text, padded y) rather than the raw text span — that is what the truth common
band expects. Per-page bands track even/odd + jitter automatically (they derive
from that page's text). Extractable repeated watermark text is detected by
content pattern; rotated/morph/image-like watermarks remain a limitation but are
reported, never silently skipped.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from .models import PageExtract

MARGIN = 86.0            # body zone margin (figure/table inference)
_COMMON_MARGIN = 48.0    # header/footer band x-range (page content margin)
_TOP_BAND = 80.0
_BOT_BAND = 80.0
_BAND_BASE = 35.0        # single-line header/footer band height
_BAND_PER_LINE = 6.0     # extra height per additional merged line
_MERGE_GAP = 4.0         # vertical gap to merge adjacent header/footer lines

# Extractable watermark text patterns (content, not case ids).
_WM_RE = re.compile(r"^(CONFIDENTIAL|DRAFT)\b|^Licensed to\b", re.IGNORECASE)


def body_zone(height: float) -> tuple[float, float]:
    return (MARGIN, height - MARGIN)


def _norm(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", (text or "").strip().lower()))


def _merge_lines(lines: List) -> List[List]:
    """Merge vertically-adjacent margin lines into multi-line blocks."""
    lines = sorted(lines, key=lambda l: l.bbox[1])
    blocks: List[List] = []
    for ln in lines:
        if blocks and (ln.bbox[1] - blocks[-1][-1].bbox[3]) < _MERGE_GAP:
            blocks[-1].append(ln)
        else:
            blocks.append([ln])
    return blocks


def _band(block: List, kind: str, page_w: float, region_id: str) -> dict:
    text = "\n".join(l.text for l in block)
    top = min(l.bbox[1] for l in block)
    height = _BAND_BASE + _BAND_PER_LINE * (len(block) - 1)
    bbox = [_COMMON_MARGIN, round(top, 2), round(page_w - _COMMON_MARGIN, 2), round(top + height, 2)]
    return {"kind": kind, "bbox": bbox, "text": text, "common_region_id": region_id}


def detect_common_regions(pages: List[PageExtract]) -> List[List[dict]]:
    """Return per-page list of {kind, bbox, text, common_region_id} bands."""
    out: List[List[dict]] = [[] for _ in pages]
    # Stable common_region_id by normalized text across pages (page number /
    # subtitle / jitter insensitive) so even/odd + jitter keep one group id.
    norm_to_id: Dict[str, str] = {}
    hdr_n = ftr_n = wm_n = 0

    for pi, p in enumerate(pages):
        h = p.height
        top_lines = [ln for ln in p.lines if ln.bbox[1] < _TOP_BAND]
        bot_lines = [ln for ln in p.lines if ln.bbox[3] > h - _BOT_BAND]

        for kind, lines in (("header", top_lines), ("footer", bot_lines)):
            for block in _merge_lines(lines):
                key = kind + "|" + "|".join(_norm(l.text) for l in block)
                if key not in norm_to_id:
                    if kind == "header":
                        hdr_n += 1
                        norm_to_id[key] = f"hdr_{hdr_n:03d}"
                    else:
                        ftr_n += 1
                        norm_to_id[key] = f"ftr_{ftr_n:03d}"
                out[pi].append(_band(block, kind, p.width, norm_to_id[key]))

        # Extractable watermark text (anywhere on the page).
        for ln in p.lines:
            if _WM_RE.match(ln.text.strip()):
                key = "wm|" + _norm(ln.text)
                if key not in norm_to_id:
                    wm_n += 1
                    norm_to_id[key] = f"wm_{wm_n:03d}"
                b = ln.bbox
                out[pi].append({"kind": "watermark",
                                "bbox": [max(0.0, b[0] - 4), max(0.0, b[1] - 4),
                                         min(p.width, b[2] + 4), min(p.height, b[3] + 4)],
                                "text": ln.text, "common_region_id": norm_to_id[key]})
    return out
