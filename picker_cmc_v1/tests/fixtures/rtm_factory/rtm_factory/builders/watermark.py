from __future__ import annotations

import math
import fitz

from ..models import RegionTruth, WatermarkSpec
from ..templates import render_template


def draw_watermark(page: fitz.Page, spec: WatermarkSpec, *, page_no: int, page_offset: int) -> RegionTruth | None:
    if not spec.enabled or spec.bbox is None:
        return None
    text = render_template(
        spec.text_template,
        page=page_no,
        page_offset=page_offset,
        user=f"user{page_no}@example.test" if spec.variable_text else "fixed@example.test",
    )
    bbox = spec.bbox
    rect = fitz.Rect(*bbox.to_list())
    color = (0.65, 0.65, 0.65)
    if spec.image_like:
        page.draw_rect(rect, color=color, fill=(0.92, 0.92, 0.92), fill_opacity=max(0.04, spec.opacity), width=0.5, overlay=True)
        page.draw_line(rect.tl, rect.br, color=color, width=0.8, stroke_opacity=max(0.1, spec.opacity))
        page.draw_line(rect.bl, rect.tr, color=color, width=0.8, stroke_opacity=max(0.1, spec.opacity))
        page.insert_textbox(rect, text, fontsize=18, fontname="helv", align=1, color=color, fill_opacity=max(0.08, spec.opacity))
    elif abs(spec.rotation_deg) > 0.01:
        # PyMuPDF's rotate argument only accepts multiples of 90. Use a morph matrix for diagonal text.
        anchor = fitz.Point(bbox.x0 + bbox.width * 0.18, bbox.y0 + bbox.height * 0.58)
        matrix = fitz.Matrix(1, 1).prerotate(spec.rotation_deg)
        page.insert_text(
            anchor,
            text,
            fontsize=30,
            fontname="helv",
            color=color,
            fill_opacity=spec.opacity,
            morph=(anchor, matrix),
            overlay=True,
        )
        # Invisible-ish bbox guide for preview reality without dominating the page.
        page.draw_rect(rect, color=(0.8, 0.8, 0.8), width=0.2, stroke_opacity=0.15)
    else:
        page.insert_textbox(rect, text, fontsize=28, fontname="helv", align=1, color=color, fill_opacity=spec.opacity)
    return RegionTruth(kind="watermark", bbox=bbox, text=text, variable_text=spec.variable_text, rotation_deg=spec.rotation_deg)
