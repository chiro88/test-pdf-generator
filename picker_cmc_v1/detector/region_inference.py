"""Heuristic figure/table body + context inference from drawing clusters (D11).

No truth is used. Vector drawings (RTM draws figure boxes / table grids / curves
with draw_rect/draw_line) are clustered vertically; each caption anchor is
assigned the nearest unused cluster as its body band. title_position is inferred
from whether the body sits above (caption below) or below (caption above) the
caption. This is a baseline — body bbox accuracy is allowed to be rough.
"""
from __future__ import annotations

from typing import List, Optional, Set

from .models import InferredRegion

_LINE = 12.0
_CLUSTER_GAP = 24.0
_CONTEXT_MARGIN = 8.0
_CAP_PAD_TOP = 1.0
_CAP_PAD_BOTTOM = 10.0


_CONTENT_MARGIN = 54.0


def caption_band(caption_lines: List[List[float]], body_bbox, page_w: float) -> List[float]:
    """Expand the caption text line(s) into a caption BAND.

    RTM captions span the content column (page margins), not just the text run,
    so x-range = [margin, page_w - margin] (clamped to include the text). y-range
    is the merged caption text bbox + small padding. Multiline captions merge.
    """
    ty0 = min(l[1] for l in caption_lines)
    ty1 = max(l[3] for l in caption_lines)
    tx0 = min(l[0] for l in caption_lines)
    tx1 = max(l[2] for l in caption_lines)
    return [
        max(0.0, min(_CONTENT_MARGIN, tx0)),
        max(0.0, ty0 - _CAP_PAD_TOP),
        min(page_w, max(page_w - _CONTENT_MARGIN, tx1)),
        ty1 + _CAP_PAD_BOTTOM,
    ]


def cluster_drawings(drawings: List[List[float]], zone: tuple[float, float]) -> List[List[float]]:
    """Merge drawing rects (within the body zone) into vertical clusters."""
    z0, z1 = zone
    rects = [r for r in drawings if r[3] >= z0 - 4 and r[1] <= z1 + 4 and (r[2] - r[0]) > 6 and (r[3] - r[1]) > 2]
    rects.sort(key=lambda r: r[1])
    clusters: List[List[float]] = []
    for r in rects:
        if clusters and r[1] - clusters[-1][3] < _CLUSTER_GAP:
            c = clusters[-1]
            clusters[-1] = [min(c[0], r[0]), min(c[1], r[1]), max(c[2], r[2]), max(c[3], r[3])]
        else:
            clusters.append(list(r))
    return clusters


def infer_region(caption_bbox: List[float], clusters: List[List[float]], used: Set[int],
                 page_w: float, page_h: float) -> Optional[InferredRegion]:
    cap_cy = (caption_bbox[1] + caption_bbox[3]) / 2
    best = None
    best_d = 1e9
    for i, c in enumerate(clusters):
        if i in used:
            continue
        ccy = (c[1] + c[3]) / 2
        d = abs(ccy - cap_cy)
        if d < best_d:
            best_d, best = d, i
    if best is None:
        return None
    used.add(best)
    body = list(clusters[best])
    body_cy = (body[1] + body[3]) / 2
    if body_cy < cap_cy:
        title_position = "below"      # body above caption -> caption is below body
        gap = caption_bbox[1] - body[3]
    else:
        title_position = "above"
        gap = body[1] - caption_bbox[3]
    gap_lines = int(round(max(0.0, gap) / _LINE))
    ctx = [
        max(0.0, min(caption_bbox[0], body[0]) - _CONTEXT_MARGIN),
        max(0.0, min(caption_bbox[1], body[1]) - _CONTEXT_MARGIN),
        min(page_w, max(caption_bbox[2], body[2]) + _CONTEXT_MARGIN),
        min(page_h, max(caption_bbox[3], body[3]) + _CONTEXT_MARGIN),
    ]
    return InferredRegion(body=body, context=ctx, title_position=title_position, title_body_gap_lines=gap_lines)
