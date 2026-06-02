from __future__ import annotations

import math
import fitz

from ..layout import context_from
from ..models import FigureSpec, FigureTruth
from ..templates import FIGURE_CAPTION_TEMPLATES


def _draw_waveform(page: fitz.Page, rect: fitz.Rect) -> None:
    page.draw_rect(rect, color=(0, 0, 0), width=0.8)
    mid_y = (rect.y0 + rect.y1) / 2
    page.draw_line((rect.x0 + 10, mid_y), (rect.x1 - 10, mid_y), color=(0.25, 0.25, 0.25), width=0.4)
    x = rect.x0 + 16
    step = max(20, rect.width / 12)
    last = (x, mid_y)
    for i in range(1, 13):
        nx = rect.x0 + 16 + i * step
        ny = mid_y - math.sin(i * math.pi / 2) * rect.height * 0.26
        page.draw_line(last, (nx, ny), color=(0.1, 0.1, 0.1), width=1.2)
        last = (nx, ny)
    for k in range(4):
        tx = rect.x0 + 30 + k * step * 3
        page.draw_line((tx, rect.y0 + 12), (tx, rect.y1 - 12), color=(0.55, 0.55, 0.55), width=0.3)
        page.insert_text((tx + 2, rect.y1 - 18), f"t{k}", fontsize=7, color=(0.2, 0.2, 0.2))


def _draw_diagram(page: fitz.Page, rect: fitz.Rect) -> None:
    page.draw_rect(rect, color=(0, 0, 0), width=0.8)
    box_w = rect.width / 4
    y = rect.y0 + rect.height * 0.35
    blocks = []
    for i, label in enumerate(["ADC", "DSP", "FIFO"]):
        x = rect.x0 + 25 + i * (box_w + 20)
        r = fitz.Rect(x, y, x + box_w, y + 45)
        blocks.append(r)
        page.draw_rect(r, color=(0.1, 0.1, 0.1), fill=(0.94, 0.94, 0.94), width=0.8)
        page.insert_textbox(r, label, fontsize=10, align=1)
    for a, b in zip(blocks, blocks[1:]):
        ymid = (a.y0 + a.y1) / 2
        page.draw_line((a.x1, ymid), (b.x0, ymid), color=(0, 0, 0), width=1.0)
        page.draw_line((b.x0, ymid), (b.x0 - 5, ymid - 4), color=(0, 0, 0), width=1.0)
        page.draw_line((b.x0, ymid), (b.x0 - 5, ymid + 4), color=(0, 0, 0), width=1.0)


def _draw_raster_like(page: fitz.Page, rect: fitz.Rect) -> None:
    page.draw_rect(rect, color=(0, 0, 0), width=0.8)
    rows = 8
    cols = 10
    cell_w = rect.width / cols
    cell_h = rect.height / rows
    for r in range(rows):
        for c in range(cols):
            tone = 0.78 + ((r * 3 + c * 5) % 13) / 100
            cell = fitz.Rect(rect.x0 + c * cell_w, rect.y0 + r * cell_h, rect.x0 + (c + 1) * cell_w, rect.y0 + (r + 1) * cell_h)
            page.draw_rect(cell, color=(tone, tone, tone), fill=(tone, tone, tone), width=0.1)


def draw_figure(page: fitz.Page, spec: FigureSpec, *, page_width: float, page_height: float) -> FigureTruth:
    body_rect = fitz.Rect(*spec.body_region.to_list())
    if spec.body_template == "waveform":
        _draw_waveform(page, body_rect)
    elif spec.body_template == "diagram":
        _draw_diagram(page, body_rect)
    elif spec.body_template == "mixed":
        _draw_diagram(page, body_rect)
        _draw_waveform(page, fitz.Rect(body_rect.x0 + 12, body_rect.y1 - 55, body_rect.x1 - 12, body_rect.y1 - 12))
    else:
        _draw_raster_like(page, body_rect)

    caption_text = FIGURE_CAPTION_TEMPLATES[spec.alias].format(index=spec.index, title=spec.title)
    page.insert_textbox(fitz.Rect(*spec.caption_region.to_list()), caption_text, fontsize=9, fontname="helv", align=0)
    context = context_from(spec.caption_region, spec.body_region, spec.context_margin, page_width, page_height)
    if spec.caption_position == "below":
        gap_pt = spec.caption_region.y0 - spec.body_region.y1
    else:
        gap_pt = spec.body_region.y0 - spec.caption_region.y1
    return FigureTruth(
        kind="figure",
        index=spec.index,
        title=spec.title,
        caption_region=spec.caption_region,
        body_region=spec.body_region,
        context_region=context,
        body_kind=spec.body_template,
        title_position=spec.caption_position,
        title_body_gap_lines=int(round(max(0.0, gap_pt) / 12.0)),
    )
