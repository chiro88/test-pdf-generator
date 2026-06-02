from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz

from .builders.figure import draw_figure
from .builders.header_footer import draw_header_or_footer
from .builders.negative import draw_negative_text
from .builders.table import draw_table
from .builders.watermark import draw_watermark
from .layout import assert_bbox_in_page, page_dimensions
from .models import CaseSpec, PageTruth


def render_png(page: fitz.Page, scale: float = 110 / 72) -> bytes:
    return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")


def _add_body_filler(page: fitz.Page, width: float, height: float, page_no: int, columns: int) -> None:
    left = 54.0
    right = width - 54.0
    top = 86.0
    bottom = height - 86.0
    col_gap = 22.0
    col_w = (right - left - (columns - 1) * col_gap) / columns
    filler = (
        "This synthetic paragraph exercises realistic page texture without carrying copyrighted source text. "
        "It intentionally includes ordinary engineering prose, numeric values, and references that should not be detected as captions."
    )
    for col in range(columns):
        x0 = left + col * (col_w + col_gap)
        rect = fitz.Rect(x0, top, x0 + col_w, bottom)
        text = "\n".join([filler for _ in range(4 if columns == 2 else 6)])
        page.insert_textbox(rect, text, fontsize=8, fontname="helv", color=(0.18, 0.18, 0.18), lineheight=1.15)


def build_pdf(case: CaseSpec, case_dir: Path) -> Tuple[dict, List[Path]]:
    from .truth import case_truth_json, write_truth

    width, height = page_dimensions(case.page.size, case.page.orientation)
    doc = fitz.open()
    page_truths: List[PageTruth] = []

    for page_no in range(1, case.page.page_count + 1):
        page = doc.new_page(width=width, height=height)
        page_truth = PageTruth(page=page_no, width=width, height=height)
        _add_body_filler(page, width, height, page_no, case.page.columns)

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
