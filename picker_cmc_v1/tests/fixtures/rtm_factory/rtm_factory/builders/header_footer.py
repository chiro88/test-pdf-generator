from __future__ import annotations

import fitz

from ..layout import mirrored_x_bbox
from ..models import HeaderFooterSpec, RegionTruth
from ..templates import render_template


def draw_header_or_footer(page: fitz.Page, spec: HeaderFooterSpec, *, kind: str, page_no: int, page_offset: int, page_width: float) -> RegionTruth | None:
    if not spec.enabled or spec.bbox is None:
        return None
    if spec.support_pages is not None and page_no not in spec.support_pages:
        return None
    bbox = spec.bbox
    if spec.mirrored_even_odd and page_no % 2 == 0:
        bbox = mirrored_x_bbox(bbox, page_width)
    text = render_template(
        spec.text_template,
        page=page_no,
        page_offset=page_offset,
        subtitle=f"Section {page_no % 4 + 1}",
        user="rtm@example.test",
    )
    rect = fitz.Rect(*bbox.to_list())
    page.insert_textbox(rect, text, fontsize=9, fontname="helv", align=1, color=(0.1, 0.1, 0.1))
    if spec.rule_line:
        y = bbox.y1 if kind == "header" else bbox.y0
        page.draw_line((bbox.x0, y), (bbox.x1, y), color=(0.25, 0.25, 0.25), width=0.5)
    return RegionTruth(kind=kind, bbox=bbox, text=text, variable_text=spec.variable_text)
