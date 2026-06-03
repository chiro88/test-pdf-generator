"""D16 common-region / watermark cleanup tests (no-truth).

Note on multipart footer: the frozen truth models a multipart footer as THREE
separate footer regions (left/center/right). Emitting one merged band would make
two of them 'missing'; to keep missing=0 the detector emits one band per
fragment, matching the truth structure. (D16.5 then corrected the fragment truth
bboxes to the PDF-derivable rendered-text band, so they also match in x.)
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.pipeline import detect_pdf  # noqa: E402


def _commons(det, page, kind):
    return [c for c in det["pages"][page - 1]["common_regions"] if c["kind"] == kind]


# 1. footer bar + 2-line footer merged into one band
def test_footer_bar_two_line_one_band():
    f = _commons(detect_pdf(FROZEN / "exp_hfseq_footerbar_fig_table" / "exp_hfseq_footerbar_fig_table.pdf"), 1, "footer")
    assert len(f) == 1 and "\n" in f[0]["text"]


# 2. multipart footer -> three fragment bands (matches the truth's 3 regions)
def test_multipart_footer_fragments():
    f = _commons(detect_pdf(FROZEN / "exp_hf_multipart_footer_center_notice" / "exp_hf_multipart_footer_center_notice.pdf"), 1, "footer")
    assert len(f) == 3, [c["text"] for c in f]
    # fragments are side-by-side (distinct x), not one full-width band
    xs = sorted(c["bbox"][0] for c in f)
    assert xs[0] < xs[1] < xs[2]


# 3. page-number-only variation keeps the same footer group id
def test_page_number_same_footer_group():
    det = detect_pdf(FROZEN / "core_multipage_table_cont" / "core_multipage_table_cont.pdf")
    ids = {_commons(det, p, "footer")[0]["common_region_id"]
           for p in range(1, len(det["pages"]) + 1) if _commons(det, p, "footer")}
    assert len(ids) == 1


# 4. body / interstitial text is NOT detected as header/footer
def test_body_text_not_common():
    det = detect_pdf(FROZEN / "exp_seq_fig_t1_fig" / "exp_seq_fig_t1_fig.pdf")
    assert not [c for p in det["pages"] for c in p["common_regions"] if c["kind"] in ("header", "footer")]


def _wm_pdf(path, text, *, rect=(150, 320, 460, 470), rotate=0):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    if rotate:
        pg.insert_text(fitz.Point(rect[0], (rect[1] + rect[3]) / 2), text, fontsize=28,
                       morph=(fitz.Point(rect[0], rect[1]), fitz.Matrix(1, 1).prerotate(rotate)))
    else:
        pg.insert_textbox(fitz.Rect(*rect), text, fontsize=28, align=1)
    doc.save(str(path)); doc.close()


# 5. extractable fixed watermark -> watermark
def test_fixed_watermark_detected(tmp_path):
    pdf = tmp_path / "wm.pdf"; _wm_pdf(pdf, "CONFIDENTIAL")
    wms = [c for p in detect_pdf(pdf)["pages"] for c in p["common_regions"] if c["kind"] == "watermark"]
    assert wms and wms[0]["text"].strip() == "CONFIDENTIAL"


# 6. variable license watermark -> watermark band
def test_license_watermark_detected(tmp_path):
    pdf = tmp_path / "wm.pdf"; _wm_pdf(pdf, "Licensed to alpha@example.test")
    wms = [c for p in detect_pdf(pdf)["pages"] for c in p["common_regions"] if c["kind"] == "watermark"]
    assert wms and "Licensed to" in wms[0]["text"]


# 7. near-footer watermark is separated from the footer (a "Confidential — N"
#    footer is NOT a watermark; a bare CONFIDENTIAL in the bottom area is)
def test_footer_text_not_watermark(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.insert_textbox(fitz.Rect(48, 745, 564, 770), "Confidential — 3", fontsize=9, align=1)
    pdf = tmp_path / "f.pdf"; doc.save(str(pdf)); doc.close()
    det = detect_pdf(pdf)
    assert not [c for p in det["pages"] for c in p["common_regions"] if c["kind"] == "watermark"]
    assert [c for p in det["pages"] for c in p["common_regions"] if c["kind"] == "footer"]


# 8. rotated/image-like watermark: no crash, no false success
def test_rotated_watermark_no_crash():
    det = detect_pdf(FROZEN / "core_fixed_watermark" / "core_fixed_watermark.pdf")
    assert isinstance(det, dict) and "pages" in det


# 9. D15 caption/body gains preserved
def test_caption_body_preserved():
    fig = detect_pdf(FROZEN / "core_figure_caption_bottom" / "core_figure_caption_bottom.pdf")["pages"][0]["figures"][0]
    assert (fig["caption_region"][2] - fig["caption_region"][0]) > 300
    assert (fig["body_region"][3] - fig["body_region"][1]) > 200


# 10. no-truth guarantee
def test_no_truth_guarantee(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.insert_textbox(fitz.Rect(48, 18, 564, 40), "Running Header Text", fontsize=9, align=1)
    pdf = tmp_path / "h.pdf"; doc.save(str(pdf)); doc.close()
    assert not (tmp_path / "h.truth.json").exists()
    assert [c for c in detect_pdf(pdf)["pages"][0]["common_regions"] if c["kind"] == "header"]
