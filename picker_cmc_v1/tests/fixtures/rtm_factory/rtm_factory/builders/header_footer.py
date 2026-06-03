from __future__ import annotations

import fitz

from ..layout import jittered_bbox, mirrored_x_bbox
from ..models import HeaderFooterSpec, RegionTruth
from ..templates import render_template
from ._textband import footer_fragment_band


def draw_header_or_footer(page: fitz.Page, spec: HeaderFooterSpec, *, kind: str, page_no: int, page_offset: int, page_width: float, page_count: int = 1) -> RegionTruth | None:
    if not spec.enabled or spec.bbox is None:
        return None
    if spec.first_page_suppressed and page_no == 1:
        return None
    if spec.support_pages is not None and page_no not in spec.support_pages:
        return None
    bbox = spec.bbox
    if spec.mirrored_even_odd and page_no % 2 == 0:
        bbox = mirrored_x_bbox(bbox, page_width)
    # Deterministic per-page jitter -> truth records the ACTUAL per-page bbox.
    if spec.jitter_x or spec.jitter_y:
        bbox = jittered_bbox(bbox, page_no, spec.jitter_x, spec.jitter_y)
    text = render_template(
        spec.text_template,
        page=page_no,
        page_offset=page_offset,
        subtitle=f"Section {page_no % 4 + 1}",
        user="rtm@example.test",
        pages=page_count,
    )
    rect = fitz.Rect(*bbox.to_list())
    page.insert_textbox(rect, text, fontsize=9, fontname="helv", align=1, color=(0.1, 0.1, 0.1))
    if spec.rule_line:
        ry = (bbox.y1 if kind == "header" else bbox.y0)
        if spec.rule_jitter_y:
            ry += ((page_no * 3) % (2 * spec.rule_jitter_y + 1)) - spec.rule_jitter_y
        page.draw_line((bbox.x0, ry), (bbox.x1, ry), color=(0.25, 0.25, 0.25), width=0.5)
    if spec.band_from_text:
        # D16.5: record the PDF-derivable rendered-text band (matches the detector)
        # instead of the authored editorial bbox.
        band = footer_fragment_band(page, rect, page_width)
        if band is not None:
            bbox = band
    return RegionTruth(kind=kind, bbox=bbox, text=text, variable_text=spec.variable_text)
