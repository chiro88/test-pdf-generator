"""D24 coordinate helpers (canonical; the JS frontend mirrors these).

The page is rendered at ``scale``; the image is page_pt * scale pixels. Conversion
keeps the PDF-pt / top-left origin with NO y-flip.
"""
from __future__ import annotations

from typing import Dict, List


def screen_to_pdf_pt(px: float, scale: float) -> float:
    """A screen pixel offset (from the page top-left) back to a PDF point."""
    return px / scale


def pdf_pt_to_screen(pt: float, scale: float) -> float:
    return pt * scale


def ruler_measure(start: List[float], end: List[float]) -> Dict[str, float]:
    """Measurement between two PDF-pt points (ruler mode; not persisted)."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return {"start": list(start), "end": list(end),
            "dx": round(dx, 2), "dy": round(dy, 2),
            "distance": round((dx * dx + dy * dy) ** 0.5, 2)}
