"""Figure/table body + context inference (D14).

No truth. RTM figures/tables draw a frame rect (the body box / table grid frame)
plus internal strokes (waveform/grid lines) that overshoot the frame. D14 picks
the dominant FRAME rect (largest-area drawing) as the body — which fixes the
x-overshoot of the D11 cluster-union — and is column-aware: the body frame must
x-overlap the caption text column, so two-column figures don't bleed across
columns. caption_region then follows the body x-range, and context_region is
union(caption, body)+margin clamped to the page and to sequence neighbours.
"""
from __future__ import annotations

from typing import List, Optional, Set

from .models import InferredRegion

_LINE = 12.0
_CONTEXT_MARGIN = 8.0
_CAP_PAD_TOP = 1.0
_CAP_PAD_BOTTOM = 10.0
_CONTENT_MARGIN = 54.0
_MIN_FRAME_AREA = 8000.0
_MIN_FRAME_W = 100.0
_MIN_FRAME_H = 24.0


def frames(drawings: List[List[float]], zone: tuple[float, float]) -> List[List[float]]:
    """Dominant figure/table frame rects within the body zone (drops thin lines / tiny cells)."""
    z0, z1 = zone
    out = []
    for r in drawings:
        w, h = r[2] - r[0], r[3] - r[1]
        if r[3] >= z0 - 4 and r[1] <= z1 + 4 and w >= _MIN_FRAME_W and h >= _MIN_FRAME_H and w * h >= _MIN_FRAME_AREA:
            out.append([r[0], r[1], r[2], r[3]])
    return out


def _x_overlap(a, x0, x1) -> bool:
    return not (a[2] <= x0 + 2 or a[0] >= x1 - 2)


def infer_region(caption_text_bbox: List[float], frame_list: List[List[float]], used: Set[int],
                 page_w: float, page_h: float) -> Optional[InferredRegion]:
    cap_cy = (caption_text_bbox[1] + caption_text_bbox[3]) / 2
    cx0, cx1 = caption_text_bbox[0], caption_text_bbox[2]
    cands = [(i, f) for i, f in enumerate(frame_list) if i not in used and _x_overlap(f, cx0, cx1)]
    if not cands:
        cands = [(i, f) for i, f in enumerate(frame_list) if i not in used]
    if not cands:
        return None

    def y_dist(f):
        return min(abs(cap_cy - f[1]), abs(cap_cy - f[3]))

    # nearest frame by y; tie-break toward larger area (the enclosing frame, not an inner block)
    best = min(cands, key=lambda t: (round(y_dist(t[1]), 1), -((t[1][2] - t[1][0]) * (t[1][3] - t[1][1]))))
    i, body = best[0], list(best[1])
    used.add(i)

    body_cy = (body[1] + body[3]) / 2
    if body_cy < cap_cy:
        title_position = "below"
        gap = caption_text_bbox[1] - body[3]
    else:
        title_position = "above"
        gap = body[1] - caption_text_bbox[3]
    gap_lines = int(round(max(0.0, gap) / _LINE))
    return InferredRegion(body=body, context=[], title_position=title_position, title_body_gap_lines=gap_lines)


def caption_band(caption_lines: List[List[float]], body_bbox, page_w: float) -> List[float]:
    """Caption band: x follows the body column (RTM caption spans the body width);
    y is the merged caption text bbox + padding."""
    if body_bbox:
        x0, x1 = body_bbox[0], body_bbox[2]
    else:
        x0, x1 = _CONTENT_MARGIN, page_w - _CONTENT_MARGIN
    ty0 = min(l[1] for l in caption_lines)
    ty1 = max(l[3] for l in caption_lines)
    return [
        max(0.0, min(x0, min(l[0] for l in caption_lines))),
        max(0.0, ty0 - _CAP_PAD_TOP),
        min(page_w, max(x1, max(l[2] for l in caption_lines))),
        ty1 + _CAP_PAD_BOTTOM,
    ]


def context_region(cap_band: List[float], body: List[float], page_w: float, page_h: float,
                   y_lo: float = 0.0, y_hi: float | None = None) -> List[float]:
    """union(caption, body) + margin, clamped to the page and to sequence neighbours."""
    if y_hi is None:
        y_hi = page_h
    return [
        max(0.0, min(cap_band[0], body[0]) - _CONTEXT_MARGIN),
        max(y_lo, min(cap_band[1], body[1]) - _CONTEXT_MARGIN),
        min(page_w, max(cap_band[2], body[2]) + _CONTEXT_MARGIN),
        min(y_hi, max(cap_band[3], body[3]) + _CONTEXT_MARGIN),
    ]
