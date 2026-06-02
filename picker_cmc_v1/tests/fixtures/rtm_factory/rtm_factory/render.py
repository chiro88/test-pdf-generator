from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz

from .builders.figure import draw_figure
from .builders.header_footer import draw_header_or_footer
from .builders.negative import draw_negative_text
from .builders.table import draw_table
from .builders.watermark import draw_watermark
from .layout import assert_bbox_in_page, band, context_from, free_y_bands, page_dimensions
from .models import BBox, CaseSpec, PageTruth


def render_png(page: fitz.Page, scale: float = 110 / 72) -> bytes:
    return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")


_FILLER_SENTENCE = (
    "This synthetic body paragraph provides ordinary page texture without copyrighted source text; "
    "it carries numeric values and inline references that must not be detected as a caption or table."
)
_BODY_TOP = 86.0
_BODY_MARGIN = 86.0
_MIN_BAND = 34.0  # skip gaps too small to hold readable body text


def _page_target_rects(case: CaseSpec, page_no: int, width: float, height: float):
    """Context rectangles that body filler must avoid on this page (targets + negatives)."""
    rects = []
    for fig in case.figures:
        if fig.page == page_no:
            rects.append(context_from(fig.caption_region, fig.body_region, fig.context_margin, width, height))
    for tbl in case.tables:
        if tbl.page == page_no:
            rects.append(context_from(tbl.caption_region, tbl.body_region, tbl.context_margin, width, height))
    for neg in case.negative_texts:
        if neg.page == page_no:
            rects.append(neg.bbox)
    return rects


def _add_body_filler(page: fitz.Page, case: CaseSpec, page_no: int, width: float, height: float):
    """Target-aware filler: fill ONLY the free interstitial bands, never the
    figure/table target regions. Returns the BBox of each filled band so they
    can be recorded as non-target text regions in truth."""
    left = 54.0
    right = width - 54.0
    top = _BODY_TOP
    bottom = height - _BODY_MARGIN
    columns = case.page.columns
    col_gap = 22.0
    col_w = (right - left - (columns - 1) * col_gap) / columns
    targets = _page_target_rects(case, page_no, width, height)

    placed: List[BBox] = []
    for col in range(columns):
        x0 = left + col * (col_w + col_gap)
        x1 = x0 + col_w
        occupied = [(r.y0, r.y1) for r in targets if not (r.x1 <= x0 or r.x0 >= x1)]
        for by0, by1 in free_y_bands(top, bottom, occupied, _MIN_BAND):
            rect = fitz.Rect(x0, by0, x1, by1)
            # Size the text to the band so insert_textbox actually renders it
            # (it draws nothing if the full string overflows). Budget chars from
            # band capacity, then trim with a safety factor.
            chars_per_line = max(10, int(col_w / 4.3))
            visual_lines = max(1, int((by1 - by0) / (8 * 1.3)))
            budget = int(chars_per_line * visual_lines * 0.85)
            unit = _FILLER_SENTENCE + " "
            text = (unit * (budget // len(unit) + 1))[:budget].rstrip()
            page.insert_textbox(rect, text, fontsize=8, fontname="helv", color=(0.18, 0.18, 0.18), lineheight=1.3)
            placed.append(band(x0, by0, x1, by1))
    return placed


def build_pdf(case: CaseSpec, case_dir: Path) -> Tuple[dict, List[Path]]:
    from .truth import case_truth_json, write_truth

    width, height = page_dimensions(case.page.size, case.page.orientation)
    doc = fitz.open()
    page_truths: List[PageTruth] = []

    for page_no in range(1, case.page.page_count + 1):
        page = doc.new_page(width=width, height=height)
        page_truth = PageTruth(page=page_no, width=width, height=height)
        page_truth.non_target_text_regions.extend(_add_body_filler(page, case, page_no, width, height))

        for kind, spec in (("header", case.header), ("footer", case.footer)):
            region = draw_header_or_footer(page, spec, kind=kind, page_no=page_no, page_offset=case.page.page_offset, page_width=width, page_count=case.page.page_count)
            if region is not None:
                assert_bbox_in_page(region.bbox, width, height, f"{case.case_id}:{kind}")
                page_truth.common_regions.append(region)

        for extra in case.extra_regions:
            region = draw_header_or_footer(page, extra, kind=extra.kind, page_no=page_no, page_offset=case.page.page_offset, page_width=width, page_count=case.page.page_count)
            if region is not None:
                assert_bbox_in_page(region.bbox, width, height, f"{case.case_id}:{extra.kind}")
                page_truth.common_regions.append(region)

        wm = draw_watermark(page, case.watermark, page_no=page_no, page_offset=case.page.page_offset)
        if wm is not None:
            assert_bbox_in_page(wm.bbox, width, height, f"{case.case_id}:watermark")
            page_truth.common_regions.append(wm)

        for neg in case.negative_texts:
            if neg.page == page_no:
                assert_bbox_in_page(neg.bbox, width, height, f"{case.case_id}:negative")
                draw_negative_text(page, neg)

        for fig in case.figures:
            if fig.page == page_no:
                assert_bbox_in_page(fig.caption_region, width, height, f"{case.case_id}:fig_caption")
                assert_bbox_in_page(fig.body_region, width, height, f"{case.case_id}:fig_body")
                page_truth.figures.append(draw_figure(page, fig, page_width=width, page_height=height))

        for tbl in case.tables:
            if tbl.page == page_no:
                assert_bbox_in_page(tbl.caption_region, width, height, f"{case.case_id}:tbl_caption")
                assert_bbox_in_page(tbl.body_region, width, height, f"{case.case_id}:tbl_body")
                page_truth.tables.append(draw_table(page, tbl, page_width=width, page_height=height))

        page_truths.append(page_truth)

    case_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = case_dir / f"{case.case_id}.pdf"
    doc.save(str(pdf_path), garbage=4, deflate=True)

    png_paths: List[Path] = []
    for idx in range(doc.page_count):
        png_path = case_dir / f"{case.case_id}.p{idx + 1:02d}.png"
        png_path.write_bytes(render_png(doc[idx]))
        png_paths.append(png_path)

    truth = case_truth_json(case, page_truths)
    write_truth(case_dir / f"{case.case_id}.truth.json", truth)
    (case_dir / f"{case.case_id}.notes.md").write_text(case.notes.strip() + "\n", encoding="utf-8")
    doc.close()
    return truth, png_paths
