"""D16.5: derive a PDF-visible text band from a rendered page region.

The no-truth detector locates header/footer/watermark text with PyMuPDF
``get_text`` and then pads it into a band. When a truth region is authored as a
wide editorial rectangle (a multipart-footer fragment, or a license watermark
centred in a big box) that band is NOT derivable from the PDF, so a truth-blind
detector can never match it. For those regions the factory records the SAME
rendered-text band the detector derives, using identical constants and the same
per-line extraction, so the truth bbox is PDF-derivable. Rotated / morph /
image-like watermarks are left as authored bands (a documented limitation)
because their text does not extract.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

import fitz

from ..models import BBox

# These MUST mirror detector/common_regions.py.
FOOTER_FRAGMENT_PAD = 3.0   # _FRAGMENT_PAD
BAND_BASE = 35.0            # _BAND_BASE
BAND_PER_LINE = 6.0        # _BAND_PER_LINE
WM_BAND_PAD = 18.0          # _WM_BAND_PAD
# Mirror detector/common_regions._WM_RE (standalone watermark text).
_WM_RE = re.compile(r"^(CONFIDENTIAL|DRAFT)$|^Licensed to\b")


def rendered_lines(page: fitz.Page, clip: fitz.Rect, *, pad: float = 2.0) -> List[Tuple[str, BBox]]:
    """(text, line-bbox) for rendered text lines intersecting ``clip``.

    Uses the same ``get_text('dict')`` line extraction the detector uses (text =
    concatenated span text, bbox = the line bbox), so bands computed from these
    match what the detector sees on the same PDF.
    """
    r = fitz.Rect(clip.x0 - pad, clip.y0 - pad, clip.x1 + pad, clip.y1 + pad)
    out: List[Tuple[str, BBox]] = []
    for blk in page.get_text("dict", clip=r).get("blocks", []):
        for ln in blk.get("lines", []):
            txt = "".join(s.get("text", "") for s in ln.get("spans", [])).strip()
            if txt:
                b = ln["bbox"]
                out.append((txt, BBox(round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2))))
    return out


def footer_fragment_band(page: fitz.Page, clip: fitz.Rect, page_width: float) -> Optional[BBox]:
    """A multipart footer fragment band: text x +/- pad, top .. top + band height."""
    lines = rendered_lines(page, clip)
    if not lines:
        return None
    x0 = min(b.x0 for _, b in lines)
    x1 = max(b.x1 for _, b in lines)
    top = min(b.y0 for _, b in lines)
    height = BAND_BASE + BAND_PER_LINE * max(0, len(lines) - 1)
    return BBox(max(0.0, x0 - FOOTER_FRAGMENT_PAD), top, min(page_width, x1 + FOOTER_FRAGMENT_PAD), top + height)


def watermark_text_band(page: fitz.Page, clip: fitz.Rect, page_width: float, page_height: float) -> Optional[BBox]:
    """Band of the standalone-watermark line (matches the detector's per-line band).

    Returns None if no extractable watermark line is present (so the caller keeps
    the authored band as a documented limitation).
    """
    for txt, b in rendered_lines(page, clip):
        if _WM_RE.match(txt):
            return BBox(
                max(0.0, b.x0 - WM_BAND_PAD),
                max(0.0, b.y0 - WM_BAND_PAD),
                min(page_width, b.x1 + WM_BAND_PAD),
                min(page_height, b.y1 + WM_BAND_PAD),
            )
    return None
