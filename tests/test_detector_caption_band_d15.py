"""D15 caption band normalization tests (no-truth)."""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.pipeline import detect_pdf  # noqa: E402


def _objs1(cid):
    det = detect_pdf(FROZEN / cid / f"{cid}.pdf")
    return det["pages"][0]["figures"] + det["pages"][0]["tables"]


# 1. single-line figure caption band expands beyond the text span
def test_single_line_figure_caption_band():
    fig = detect_pdf(FROZEN / "core_figure_caption_bottom" / "core_figure_caption_bottom.pdf")["pages"][0]["figures"][0]
    cap = fig["caption_region"]
    assert (cap[2] - cap[0]) > 300                 # band, not the ~160pt text run
    assert (cap[3] - cap[1]) > 18                  # band taller than a single text line


# 2. single-line table caption band expands beyond the text span
def test_single_line_table_caption_band():
    tbl = detect_pdf(FROZEN / "core_multipage_table_cont" / "core_multipage_table_cont.pdf")["pages"][0]["tables"][0]
    cap = tbl["caption_region"]
    assert (cap[2] - cap[0]) > 300 and (cap[3] - cap[1]) > 18


# 3. multiline figure caption merges all title lines (taller band)
def test_multiline_caption_taller():
    figs = _objs1("exp_figure_multi_raster_multiline")
    for f in figs:
        assert (f["caption_region"][3] - f["caption_region"][1]) > 30   # 2-line band


# 4. caption x-range follows the body column (two-column)
def test_caption_x_follows_column():
    figs = sorted(detect_pdf(FROZEN / "exp_two_column_multi_figures" / "exp_two_column_multi_figures.pdf")["pages"][0]["figures"],
                  key=lambda f: f["caption_region"][0])
    left, right = figs[0]["caption_region"], figs[1]["caption_region"]
    assert left[2] <= 300 and right[0] >= 300       # captions stay in their columns


# 5. wide table caption keeps a wide x-range (follows body, not content margin)
def test_wide_table_caption_wide():
    tbl = _objs1("exp_caption_above_table_wide")[0]
    cap = tbl["caption_region"]
    assert cap[0] <= 40 and cap[2] >= 570           # wide band, not clamped to [54,558]


# 6. title_position remains correct
def test_title_position_correct():
    fb = detect_pdf(FROZEN / "core_figure_caption_bottom" / "core_figure_caption_bottom.pdf")["pages"][0]["figures"][0]
    ft = detect_pdf(FROZEN / "core_figure_caption_top" / "core_figure_caption_top.pdf")["pages"][0]["figures"][0]
    assert fb["title_position"] == "below" and ft["title_position"] == "above"
    # caption below body -> caption y0 > body y0 ; above -> caption y0 < body y0
    assert fb["caption_region"][1] > fb["body_region"][1]
    assert ft["caption_region"][1] < ft["body_region"][1]


# 7. title_body_gap_lines stays a small non-negative integer
def test_gap_lines_consistent():
    for f in _objs1("exp_seq_fig_fig"):
        assert isinstance(f["title_body_gap_lines"], int) and 0 <= f["title_body_gap_lines"] <= 5


# 8. body_region unchanged on a representative figure (frame rect)
def test_body_region_unchanged():
    fig = detect_pdf(FROZEN / "core_figure_caption_bottom" / "core_figure_caption_bottom.pdf")["pages"][0]["figures"][0]
    b = fig["body_region"]
    assert abs(b[0] - 54) <= 2 and abs(b[2] - 558) <= 2 and (b[3] - b[1]) > 200


# 9. no-truth guarantee
def test_no_truth_guarantee(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(54, 120, 558, 300), width=1)
    pg.insert_textbox(fitz.Rect(54, 320, 558, 360), "Figure 9-9. Title", fontsize=9)
    pdf = tmp_path / "f.pdf"; doc.save(str(pdf)); doc.close()
    assert not (tmp_path / "f.truth.json").exists()
    cap = detect_pdf(pdf)["pages"][0]["figures"][0]["caption_region"]
    assert (cap[2] - cap[0]) > 300 and (cap[3] - cap[1]) > 18
