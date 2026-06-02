"""No-truth detector pipeline: PDF -> detector-output-v0 pages (D11).

detect_pdf() reads only the PDF. It NEVER opens truth.json.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from detector_output import writer

from .anchors import find_anchors
from .common_regions import body_zone, detect_common_regions
from .pdf_extract import extract_pdf
from .region_inference import cluster_drawings, infer_region
from .title_patterns import continuation_marker


def _group_id(index: str) -> str:
    return "det_tbl_" + index.replace(".", "_").replace("-", "_")


def detect_pdf(pdf_path: str | Path) -> Dict[str, Any]:
    """Return a detector-output-v0 'pages' payload for one PDF (no truth read)."""
    pages_ex = extract_pdf(pdf_path)
    commons = detect_common_regions(pages_ex)
    out_pages: List[Dict[str, Any]] = []

    for pi, ex in enumerate(pages_ex):
        zone = body_zone(ex.height)
        clusters = cluster_drawings(ex.drawings, zone)
        used: set = set()
        figures: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []

        for anchor in find_anchors(ex):
            cap = anchor.caption_bbox
            region = infer_region(cap, clusters, used, ex.width, ex.height)
            if region is None:
                # no body cluster found — emit a degenerate body at the caption
                # (still a real, no-truth anchor; body accuracy is poor here)
                body, ctx, tpos, glines = list(cap), list(cap), "below", 0
            else:
                body, ctx, tpos, glines = region.body, region.context, region.title_position, region.title_body_gap_lines
            if anchor.kind == "figure":
                figures.append(writer.figure(anchor.index, anchor.title, cap, body, ctx,
                                             title_position=tpos, title_body_gap_lines=glines))
            else:
                marker = continuation_marker(anchor.title)
                tables.append(writer.table(anchor.index, anchor.title, _group_id(anchor.index), cap, body, ctx,
                                           part_index=1, is_continuation=bool(marker), continuation_marker=marker))

        common_regions = [writer.common_region(c["kind"], c["bbox"], c.get("text")) for c in commons[pi]]
        out_pages.append(writer.page(pi + 1, common_regions=common_regions, figures=figures, tables=tables))

    return {"pages": out_pages}
