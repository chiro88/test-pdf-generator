"""D12 tests: table identity / continuation linking + caption band normalization.

Still no-truth: the detector reads only the PDF. Truth is never opened here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.models import Anchor  # noqa: E402
from detector.pipeline import detect_pdf  # noqa: E402
from detector.table_identity import assign_table_groups, canonical_group_id  # noqa: E402
from detector.title_patterns import match_caption  # noqa: E402


# 1. canonical group id
def test_canonical_group_id():
    assert canonical_group_id("2.1") == "tbl_002_001"
    assert canonical_group_id("10.1") == "tbl_010_001"
    assert canonical_group_id("5-1") == "tbl_005_001"
    assert canonical_group_id("A.1") == "tbl_A_001"


def _tanchor(index, title):
    return Anchor(kind="table", index=index, title=title, caption_bbox=[54, 100, 200, 112])


# 2 + 3. continuation suffix -> shared group_id, incrementing part_index
def test_continuation_linking_shares_group_and_increments_part():
    anchors = [(1, _tanchor("2.1", "Register map")),
               (2, _tanchor("2.1", "Register map (cont)")),
               (3, _tanchor("2.1", "Register map (cont)"))]
    meta = assign_table_groups(anchors)
    parts = [meta[id(a)] for _, a in anchors]
    assert all(p["group_id"] == "tbl_002_001" for p in parts)
    assert [p["part_index"] for p in parts] == [1, 2, 3]
    assert [p["is_continuation"] for p in parts] == [False, True, True]
    assert parts[1]["continuation_marker"] == "(cont)"


# 4. same-index, separate non-continuation tables are NOT blindly merged
def test_same_index_separate_tables_distinct_groups():
    anchors = [(1, _tanchor("4.2", "Electrical characteristics")),
               (1, _tanchor("4.2", "Electrical characteristics"))]
    meta = assign_table_groups(anchors)
    gids = {meta[id(a)]["group_id"] for _, a in anchors}
    assert len(gids) == 2, gids  # two distinct ids, not collapsed into one


def _figure_pdf(path, caption):
    doc = fitz.open(); page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(54, 120, 558, 300), width=1)
    page.insert_textbox(fitz.Rect(54, 320, 558, 360), caption, fontsize=9)
    doc.save(str(path)); doc.close()


# 6. caption_region expands beyond the (narrow) text span to the content column
def test_caption_band_expands_x_range(tmp_path):
    pdf = tmp_path / "f.pdf"; _figure_pdf(pdf, "Figure 1-1. Short")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    cap = fig["caption_region"]
    assert cap[0] <= 54 and cap[2] >= 540, cap   # content-column width, not the ~150pt text run


# 5. multiline caption merges into one band taller than a single line
def test_multiline_caption_merges_lines(tmp_path):
    pdf = tmp_path / "m.pdf"; _figure_pdf(pdf, "Figure 2-2. A long figure title\nthat wraps to a second line")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    cap = fig["caption_region"]
    assert (cap[3] - cap[1]) > 18, f"multiline caption band too short: {cap}"


# 7. negative reference text still produces no anchors
def test_negatives_still_no_anchor():
    for text in ["Figure of merit is the ratio of useful output to input power.",
                 "Figure 3.4 is referenced for historical context only.",
                 "Table 2.1 describes the legacy configuration; not reproduced."]:
        assert match_caption(text) is None


# 8. no-truth guarantee remains (detect with no truth.json beside the PDF)
def test_no_truth_guarantee(tmp_path):
    pdf = tmp_path / "n.pdf"; _figure_pdf(pdf, "Figure 3-3. Title")
    assert not (tmp_path / "n.truth.json").exists()
    result = detect_pdf(pdf)
    assert result["pages"][0]["figures"][0]["index"] == "3-3"
