"""D14 figure/table body/context inference tests (no-truth).

Asserts sequence-aware boundaries (neighbours / interstitial text not eaten),
column-aware x-range (no two-column bleed), page-wide handling, and that
header/footer/watermark bands are not inside a body.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.pipeline import detect_pdf  # noqa: E402


def _objs(det, page):
    return det["pages"][page - 1]["figures"] + det["pages"][page - 1]["tables"]


def _y_overlap(a, b):
    return max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _rect_overlap(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


# 1-5. sequence: a target's context/body must not invade a neighbour's BODY or CAPTION
def _assert_contexts_disjoint(cid):
    det = detect_pdf(FROZEN / cid / f"{cid}.pdf")
    objs = _objs(det, 1)
    for i, a in enumerate(objs):
        for j, b in enumerate(objs):
            if i == j:
                continue
            assert _y_overlap(a["context_region"], b["body_region"]) <= 2.0, (cid, "ctx", a["index"], b["index"])
            assert _y_overlap(a["body_region"], b["caption_region"]) <= 2.0, (cid, "body-cap", a["index"], b["index"])


def test_figure_figure_contexts_disjoint():
    _assert_contexts_disjoint("exp_seq_fig_fig")


def test_figure_text_figure_excludes_interstitial():
    _assert_contexts_disjoint("exp_seq_fig_t1_fig")
    _assert_contexts_disjoint("exp_seq_fig_t2_fig")


def test_figure_text_table_boundary():
    _assert_contexts_disjoint("exp_seq_fig_t2_table")


def test_table_figure_disjoint():
    _assert_contexts_disjoint("exp_seq_table_fig")


def test_table_table_bodies_separated():
    det = detect_pdf(FROZEN / "exp_seq_table_table" / "exp_seq_table_table.pdf")
    tbls = sorted(det["pages"][0]["tables"], key=lambda t: t["body_region"][1])
    assert _y_overlap(tbls[0]["body_region"], tbls[1]["body_region"]) <= 2.0


# 6. two-column figure bodies do not bleed across columns
def test_two_column_no_bleed():
    det = detect_pdf(FROZEN / "exp_two_column_multi_figures" / "exp_two_column_multi_figures.pdf")
    figs = sorted(det["pages"][0]["figures"], key=lambda f: f["body_region"][0])
    left, right = figs[0]["body_region"], figs[1]["body_region"]
    assert left[2] <= 300 and right[0] >= 300, (left, right)
    assert _rect_overlap(left, right) == 0.0


# 7. page-wide figure stays (near) full width
def test_page_wide_figure_full_width():
    det = detect_pdf(FROZEN / "core_wide_diagram_xrange" / "core_wide_diagram_xrange.pdf")
    fig = det["pages"][0]["figures"][0]
    w = fig["body_region"][2] - fig["body_region"][0]
    assert w > 500, fig["body_region"]


# 8. header/footer/watermark bands are not inside a figure/table body
def test_common_regions_not_in_body():
    det = detect_pdf(FROZEN / "core_multipage_table_cont" / "core_multipage_table_cont.pdf")
    for p in det["pages"]:
        bodies = [o["body_region"] for o in (p["figures"] + p["tables"])]
        for c in p["common_regions"]:
            for body in bodies:
                assert _rect_overlap(c["bbox"], body) < 200.0, (c["kind"], body)


# 9. no-truth guarantee
def test_no_truth_guarantee(tmp_path):
    import fitz
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(54, 120, 558, 300), width=1)
    pg.insert_textbox(fitz.Rect(54, 320, 558, 360), "Figure 9-9. Title", fontsize=9)
    pdf = tmp_path / "f.pdf"; doc.save(str(pdf)); doc.close()
    assert not (tmp_path / "f.truth.json").exists()
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    assert fig["body_region"][2] - fig["body_region"][0] > 400  # full-width frame
