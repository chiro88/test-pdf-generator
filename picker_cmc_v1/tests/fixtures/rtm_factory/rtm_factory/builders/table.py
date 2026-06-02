from __future__ import annotations

import fitz

from ..layout import context_from
from ..models import TableSpec, TableTruth
from ..templates import TABLE_CAPTION_TEMPLATES


def _caption_text(spec: TableSpec) -> str:
    if spec.is_continuation and spec.continuation_marker:
        return TABLE_CAPTION_TEMPLATES["continued"].format(index=spec.index, title=spec.title, suffix=spec.continuation_marker)
    return TABLE_CAPTION_TEMPLATES["normal"].format(index=spec.index, title=spec.title)


def draw_table(page: fitz.Page, spec: TableSpec, *, page_width: float, page_height: float) -> TableTruth:
    caption_text = _caption_text(spec)
    page.insert_textbox(fitz.Rect(*spec.caption_region.to_list()), caption_text, fontsize=9, fontname="helv", align=0)

    rect = fitz.Rect(*spec.body_region.to_list())
    page.draw_rect(rect, color=(0, 0, 0), width=0.8)
    row_h = rect.height / spec.rows
    col_w = rect.width / spec.cols
    for r in range(1, spec.rows):
        y = rect.y0 + r * row_h
        page.draw_line((rect.x0, y), (rect.x1, y), color=(0.2, 0.2, 0.2), width=0.35)
    for c in range(1, spec.cols):
        x = rect.x0 + c * col_w
        page.draw_line((x, rect.y0), (x, rect.y1), color=(0.2, 0.2, 0.2), width=0.35)
    for c in range(spec.cols):
        page.insert_text((rect.x0 + c * col_w + 4, rect.y0 + 12), f"H{c+1}", fontsize=7)
    for r in range(1, min(spec.rows, 6)):
        page.insert_text((rect.x0 + 4, rect.y0 + r * row_h + 12), f"R{r + (spec.part_index - 1) * 10}", fontsize=7)

    context = context_from(spec.caption_region, spec.body_region, spec.context_margin, page_width, page_height)
    return TableTruth(
        kind="table",
        index=spec.index,
        title=spec.title,
        table_group_id=spec.table_group_id,
        part_index=spec.part_index,
        is_continuation=spec.is_continuation,
        continuation_marker=spec.continuation_marker,
        caption_region=spec.caption_region,
        body_region=spec.body_region,
        context_region=context,
        continued_from=spec.continued_from,
    )
