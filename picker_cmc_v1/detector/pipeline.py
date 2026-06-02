"""No-truth detector pipeline: PDF -> detector-output-v0 pages (D11 + D12).

detect_pdf() reads only the PDF. It NEVER opens truth.json.

D12 adds: canonical table_group_id + continuation linking, and caption-band
normalization (text line(s) -> caption band spanning the body width, with
multiline caption merge).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from detector_output import writer

from .anchors import find_anchors
from .common_regions import body_zone, detect_common_regions
from .pdf_extract import extract_pdf
from .region_inference import caption_band, cluster_drawings, infer_region
from .table_identity import assign_table_groups
from .title_patterns import match_caption

_LINE = 12.0
_CONTEXT_MARGIN = 8.0


def _multiline_caption(anchor_bbox: List[float], lines) -> List[List[float]]:
    """Merge the anchor caption line with directly-following title lines."""
    merged = [list(anchor_bbox)]
    cur = list(anchor_bbox)
    for ln in sorted(lines, key=lambda l: l.bbox[1]):
        b = ln.bbox
        if (b[1] > cur[1] + 0.5 and (b[1] - cur[3]) < 5.0
                and b[0] < cur[2] and b[2] > cur[0] and match_caption(ln.text) is None):
            merged.append(list(b))
            cur = list(b)
    return merged


def _context(cap_band: List[float], body: List[float], page_w: float, page_h: float) -> List[float]:
    return [
        max(0.0, min(cap_band[0], body[0]) - _CONTEXT_MARGIN),
        max(0.0, min(cap_band[1], body[1]) - _CONTEXT_MARGIN),
        min(page_w, max(cap_band[2], body[2]) + _CONTEXT_MARGIN),
        min(page_h, max(cap_band[3], body[3]) + _CONTEXT_MARGIN),
    ]


def detect_pdf(pdf_path: str | Path) -> Dict[str, Any]:
    """Return a detector-output-v0 'pages' payload for one PDF (no truth read)."""
    pages_ex = extract_pdf(pdf_path)
    commons = detect_common_regions(pages_ex)

    # Pass 1: per-page anchors + body inference + caption band.
    per_page: List[Dict[str, Any]] = []
    table_anchors = []  # (page, anchor) in reading order
    for ex in pages_ex:
        zone = body_zone(ex.height)
        clusters = cluster_drawings(ex.drawings, zone)
        used: set = set()
        records = []
        for anchor in find_anchors(ex):
            region = infer_region(anchor.caption_bbox, clusters, used, ex.width, ex.height)
            cap_lines = _multiline_caption(anchor.caption_bbox, ex.lines)
            if region is None:
                cap = caption_band(cap_lines, None, ex.width)
                body, ctx, tpos, glines = list(cap), list(cap), "below", 0
            else:
                body = region.body
                cap = caption_band(cap_lines, body, ex.width)
                ctx = _context(cap, body, ex.width, ex.height)
                tpos = region.title_position
                glines = int(round(max(0.0, (cap[1] - body[3]) if tpos == "below" else (body[1] - cap[3])) / _LINE))
            records.append({"anchor": anchor, "caption": cap, "body": body, "context": ctx,
                            "title_position": tpos, "gap_lines": glines})
            if anchor.kind == "table":
                table_anchors.append((ex.page, anchor))
        per_page.append({"page": ex.page, "records": records})

    # Cross-page table identity + continuation linking.
    table_meta = assign_table_groups(table_anchors)

    out_pages: List[Dict[str, Any]] = []
    for pi, page in enumerate(per_page):
        figures: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        for rec in page["records"]:
            a = rec["anchor"]
            if a.kind == "figure":
                figures.append(writer.figure(a.index, a.title, rec["caption"], rec["body"], rec["context"],
                                             title_position=rec["title_position"], title_body_gap_lines=rec["gap_lines"]))
            else:
                m = table_meta[id(a)]
                tables.append(writer.table(a.index, a.title, m["group_id"], rec["caption"], rec["body"], rec["context"],
                                           part_index=m["part_index"], is_continuation=m["is_continuation"],
                                           continuation_marker=m["continuation_marker"],
                                           continued_from=(m["group_id"] if m["is_continuation"] else None)))
        common_regions = [writer.common_region(c["kind"], c["bbox"], c.get("text"), c.get("common_region_id"))
                           for c in commons[pi]]
        out_pages.append(writer.page(page["page"], common_regions=common_regions, figures=figures, tables=tables))

    return {"pages": out_pages}
