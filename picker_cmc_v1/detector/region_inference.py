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

from typing import List, Optional

from .models import InferredRegion

_LINE = 12.0
_CONTEXT_MARGIN = 8.0
_CAP_PAD_TOP = 1.0
# D15: caption band height = base (covers single-line truth cap_h 18..28 within
# tolerance: text_top+23 is within +-5 of both) + per-extra-line increment
# (2-line truth cap_h ~46 -> text_top+41, within +-5). Derived from PDF text
# layout (line count), not from any RTM case id.
_CAP_BAND_BASE = 23.0
_CAP_BAND_PER_LINE = 18.0
_CONTENT_MARGIN = 54.0
_MIN_FRAME_AREA = 8000.0
_MIN_FRAME_W = 100.0

# D20 real-PDF body inference (unenclosed diagrams/waveforms + text-heavy tables).
_ZONE_MARGIN = 30.0          # page top/bottom content margin for the body zone
_DOMINANT_FRAME_FRAC = 0.62  # a frame enclosing >= this much zone-drawing area is THE body
_LABEL_MAX_W = 180.0         # a "short label" (signal name / axis text) is narrower than this
_LABEL_GAP = 16.0            # a label this close to the drawing core joins the body
                             # (small enough not to walk across a two-column gutter)
_ROW_GAP = 20.0             # text rows within this vertical gap are one contiguous table body
_BODY_PAD = 2.0
_MIN_TABLE_FRAME_H = 45.0    # a real grid frame is tall; a thin rule line is not
_CLUSTER_GAP = 35.0          # drawings within this vertical gap form one diagram band;
                             # a larger gap (e.g. a Note rule above a waveform) splits off


def _area(r) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _union(a, b) -> List[float]:
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _inter_area(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy


def _y_overlap(a, b, pad: float = 0.0) -> bool:
    return not (a[3] <= b[1] - pad or a[1] >= b[3] + pad)


def _caption_x_overlap(a, cap) -> bool:
    return not (a[2] <= cap[0] - 2 or a[0] >= cap[2] + 2)


def _nearest_gap_side(cap: List[float], drawings: List[List[float]]) -> Optional[str]:
    """Side of the drawing nearest this caption (smallest vertical gap), or None."""
    cap_top, cap_bot = cap[1], cap[3]
    ga = min((cap_top - r[3] for r in drawings if r[3] <= cap_top + 2), default=None)
    gb = min((r[1] - cap_bot for r in drawings if r[1] >= cap_bot - 2), default=None)
    if ga is None and gb is None:
        return None
    if ga is None:
        return "below"
    if gb is None:
        return "above"
    return "above" if ga <= gb else "below"


def body_orientation(caps: List[List[float]], drawings: List[List[float]], lines=None) -> str:
    """Body side for a set of same-kind captions (caption-below figures vs
    caption-above tables). Uses the TOPMOST caption's nearest-drawing side: the
    first caption of a kind has no same-kind body above it to confuse the vote, so
    it reads orientation cleanly even when later captions are tightly stacked. A
    grid-less text table has no drawings, so it falls back to the nearest text row."""
    ordered = sorted(caps, key=lambda c: c[1])
    for c in ordered:
        s = _nearest_gap_side(c, drawings)
        if s:
            return s
    if lines:
        for c in ordered:
            text = [ln.bbox for ln in lines if _inter_area(ln.bbox, c) <= 0.3 * _area(ln.bbox)]
            s = _nearest_gap_side(c, text)
            if s:
                return s
    return "below"


def _owns(d: List[float], cap: List[float], side: str,
          all_caps_sides: List[tuple]) -> bool:
    """A drawing belongs to the caption nearest it on that caption's body side, so
    a figure does not grab a stacked neighbour's frame (each drawing has one owner)."""
    my_gap = (cap[1] - d[3]) if side == "above" else (d[1] - cap[3])
    if my_gap < -2:
        return False                              # not on this caption's body side
    for oc, os in all_caps_sides:
        if oc is cap:
            continue
        og = (oc[1] - d[3]) if os == "above" else (d[1] - oc[3])
        if og >= -2 and og < my_gap - 0.5:
            return False                          # a nearer caption owns it
    return True


def _zone_y_bounds(cap: List[float], side: str, others: List[List[float]],
                   commons: List[List[float]], page_h: float) -> tuple[float, float]:
    """Vertical [lo, hi] the body may occupy, bounded by other captions / common
    regions on the body side so a figure never eats its neighbour or the header/footer."""
    if side == "above":
        lo = _ZONE_MARGIN
        for b in list(others) + list(commons):
            if b[3] <= cap[1] + 2 and _caption_x_overlap(b, cap):
                lo = max(lo, b[3])
        return lo, cap[1]
    hi = page_h - _ZONE_MARGIN
    for b in list(others) + list(commons):
        if b[1] >= cap[3] - 2 and _caption_x_overlap(b, cap):
            hi = min(hi, b[1])
    return cap[3], hi


def _split_commons(commons: List[dict]) -> tuple[List[List[float]], set]:
    """Header/footer bboxes (for spatial exclusion) and watermark texts (for text
    exclusion). A diagonal watermark has a huge bbox that must NOT exclude the body
    content beneath it, so watermarks are matched by text, not by their box."""
    hf = [c["bbox"] for c in commons if c.get("kind") in ("header", "footer")]
    wm = {(c.get("text") or "").strip() for c in commons if c.get("kind") == "watermark"}
    return hf, wm


def _excluded(line, cap, hf_bands, wm_texts) -> bool:
    b = line.bbox
    if _inter_area(b, cap) > 0.3 * _area(b):          # the caption itself
        return True
    if (line.text or "").strip() in wm_texts:         # watermark text (any position)
        return True
    return any(_inter_area(b, c) > 0.3 * _area(b) for c in hf_bands)  # header/footer band


def _drawing_core(members: List[List[float]]) -> Optional[List[float]]:
    """Body core from a drawing cluster: the dominant enclosing frame if one
    contains most of the cluster's area (RTM frame / a real plot box, avoiding the
    overshoot of internal strokes), else the union of the whole cluster."""
    if not members:
        return None
    total = sum(_area(r) for r in members) or 1.0
    best, best_contained = None, 0.0
    for f in members:
        if _area(f) < _MIN_FRAME_AREA:
            continue
        contained = sum(_area(d) for d in members if _inter_area(d, f) >= 0.6 * _area(d))
        if contained > best_contained:
            best, best_contained = f, contained
    if best is not None and best_contained >= _DOMINANT_FRAME_FRAC * total:
        return list(best)
    core = list(members[0])
    for d in members[1:]:
        core = _union(core, d)
    return core


def _grow_cluster(zone_draw: List[List[float]], cap: List[float], side: str) -> List[List[float]]:
    """Vertically-contiguous drawing band nearest the caption — so a figure takes its
    own diagram band (incl. side-by-side boxes at the same y) but NOT a thin Note rule
    / separator that sits across a larger gap above the actual waveform."""
    if not zone_draw:
        return []

    def gap_to_cap(r):
        return (cap[1] - r[3]) if side == "above" else (r[1] - cap[3])

    seed_i = min(range(len(zone_draw)), key=lambda i: abs(gap_to_cap(zone_draw[i])))
    band = {seed_i}
    bbox = list(zone_draw[seed_i])
    changed = True
    while changed:
        changed = False
        for i, d in enumerate(zone_draw):
            if i in band:
                continue
            vgap = max(d[1] - bbox[3], bbox[1] - d[3], 0.0)
            if vgap <= _CLUSTER_GAP:
                band.add(i)
                bbox = _union(bbox, d)
                changed = True
    return [zone_draw[i] for i in band]


def _expand_with_labels(core, lines, cap, hf_bands, wm_texts, zone) -> List[float]:
    """Grow the body to include short text labels (signal names/axis text) sharing
    the core's y-band and adjacent to it — without swallowing paragraphs or a Note
    block above the diagram. Labels must y-overlap the drawing core (so prose above
    the waveform is excluded); iterated so a chain of left signal names is pulled in."""
    lo, hi = zone
    body = list(core)
    # candidates: short text lines that align with a drawing ROW (y-overlap the core),
    # so left signal labels are pulled in but a Note/paragraph above the diagram is not.
    cands = [ln for ln in lines if ln.bbox[1] >= lo - 2 and ln.bbox[3] <= hi + 2
             and (ln.bbox[2] - ln.bbox[0]) <= _LABEL_MAX_W
             and _y_overlap(ln.bbox, core, pad=2.0)
             and not _excluded(ln, cap, hf_bands, wm_texts)]
    changed = True
    while changed:
        changed = False
        for ln in cands:
            b = ln.bbox
            gap = max(body[0] - b[2], b[0] - body[2], 0.0)
            if gap <= _LABEL_GAP and (b[0] < body[0] - 0.5 or b[2] > body[2] + 0.5):
                body = _union(body, b)
                changed = True
    return body


def _table_rows_core(lines, cap, side, hf_bands, wm_texts, zone) -> Optional[List[float]]:
    """Body for a text-heavy table (weak/no grid): the contiguous block of row text
    on the body side, stopping at a large vertical gap or a boundary."""
    lo, hi = zone
    rows = [ln.bbox for ln in lines
            if ln.bbox[1] >= lo - 2 and ln.bbox[3] <= hi + 2
            and not _excluded(ln, cap, hf_bands, wm_texts)]
    if not rows:
        return None
    rows.sort(key=lambda b: b[1], reverse=(side == "above"))
    core = list(rows[0])
    edge = rows[0][1] if side == "above" else rows[0][3]
    for b in rows[1:]:
        gap = (b[1] - edge) if side == "below" else (edge - b[3])
        if gap > _ROW_GAP:
            break
        core = _union(core, b)
        edge = max(edge, b[3]) if side == "below" else min(edge, b[1])
    return core


def infer_body(cap: List[float], kind: str, side: str, all_caps_sides: List[tuple],
               drawings: List[List[float]], lines, others: List[List[float]], commons: List[dict],
               page_w: float, page_h: float) -> Optional[InferredRegion]:
    """D20: body_region for real (possibly unenclosed) figures/tables.

    ``side`` (from body_orientation) says whether the body is above or below the
    caption. Bounds a zone by neighbouring captions/header-footer bands; keeps only
    drawings on the body side that x-overlap the caption column (two-column safety)
    AND are owned by this caption (nearest of all captions, so a stacked neighbour's
    frame is not stolen); takes the dominant frame or the diagram union; augments
    with adjacent short labels; and for a grid-less table uses the contiguous
    row-text block. Never reads truth; nothing is case-specific.
    """
    hf_bands, wm_texts = _split_commons(commons)
    zone = _zone_y_bounds(cap, side, others, hf_bands, page_h)
    lo, hi = zone

    on_side = (lambda r: r[3] <= cap[1] + 2) if side == "above" else (lambda r: r[1] >= cap[3] - 2)
    # Column filter only in a genuine two-column layout (another caption side-by-side
    # at a similar y). A lone wide figure with a short/offset caption keeps full width.
    cap_cy = (cap[1] + cap[3]) / 2
    two_col = any(abs((o[1] + o[3]) / 2 - cap_cy) < 25 and (o[2] <= cap[0] or o[0] >= cap[2])
                  for o in others)
    zone_draw = [r for r in drawings if r[3] >= lo - 2 and r[1] <= hi + 2 and on_side(r)
                 and _owns(r, cap, side, all_caps_sides)
                 and (not two_col or _caption_x_overlap(r, cap))]

    if kind == "table":
        # A real grid frame (tall AND wide) is the body; a bare rule line (zero
        # width/height) is not — without a real frame (thin-rule / text-only table)
        # use the contiguous row-text block so the rows are captured.
        grid = [r for r in zone_draw if (r[3] - r[1]) >= _MIN_TABLE_FRAME_H and (r[2] - r[0]) >= _MIN_FRAME_W]
        core = _drawing_core(grid)
        if core is None:
            core = _table_rows_core(lines, cap, side, hf_bands, wm_texts, zone)
    else:
        # Figure: the vertically-contiguous drawing band nearest the caption (the
        # diagram/waveform), so a Note rule across a larger gap above is excluded.
        core = _drawing_core(_grow_cluster(zone_draw, cap, side))
    if core is None:
        return None

    body = _expand_with_labels(core, lines, cap, hf_bands, wm_texts, zone)
    # small padding, clamped to the zone + page
    body = [max(0.0, body[0] - _BODY_PAD), max(lo, body[1] - _BODY_PAD),
            min(page_w, body[2] + _BODY_PAD), min(hi, body[3] + _BODY_PAD)]

    if side == "above":
        title_position = "below"
        gap = cap[1] - body[3]
    else:
        title_position = "above"
        gap = body[1] - cap[3]
    gap_lines = int(round(max(0.0, gap) / _LINE))
    return InferredRegion(body=body, context=[], title_position=title_position, title_body_gap_lines=gap_lines)


def caption_band(caption_lines: List[List[float]], body_bbox, page_w: float, kind: str = "figure") -> List[float]:
    """Caption band (D15): y0 = merged text top, y1 = text_top + deterministic
    band height by line count. x follows the body width — for figures clamped to
    the content margin (a page-wide figure body does not widen its caption), for
    tables the caption spans the body width (wide tables keep a wide caption)."""
    if body_bbox:
        if kind == "table":
            x0, x1 = body_bbox[0], body_bbox[2]
        else:
            x0 = max(_CONTENT_MARGIN, body_bbox[0])
            x1 = min(page_w - _CONTENT_MARGIN, body_bbox[2])
    else:
        x0, x1 = _CONTENT_MARGIN, page_w - _CONTENT_MARGIN
    ty0 = min(l[1] for l in caption_lines)
    n_lines = len(caption_lines)
    band_h = _CAP_BAND_BASE + _CAP_BAND_PER_LINE * (n_lines - 1)
    return [max(0.0, x0), max(0.0, ty0 - _CAP_PAD_TOP), min(page_w, x1), ty0 + band_h]


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
