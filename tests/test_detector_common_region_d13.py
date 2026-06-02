"""D13 common-region band normalization + extractable watermark tests.

Still no-truth: the detector reads only the PDF. Frozen PDFs are used as inputs;
truth is read only for the table-identity regression assertion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.pipeline import detect_pdf  # noqa: E402


def _detect(cid):
    return detect_pdf(FROZEN / cid / f"{cid}.pdf")


def _commons(det, page, kind):
    return [c for c in det["pages"][page - 1]["common_regions"] if c["kind"] == kind]


# 1. repeated 2-line header merged into one band
def test_two_line_header_band():
    h = _commons(_detect("exp_hfseq_2line_header_fig_fig"), 1, "header")
    assert len(h) == 1, h
    b = h[0]["bbox"]
    assert b[0] == 48 and b[2] == 564           # content-margin band, not the text span
    assert (b[3] - b[1]) > 35                    # two merged lines -> taller than one
    assert "\n" in h[0]["text"]


# 2. footer bar + 2-line footer in one band
def test_footer_bar_two_line_band():
    f = _commons(_detect("exp_hfseq_footerbar_fig_table"), 1, "footer")
    assert len(f) == 1 and "\n" in f[0]["text"]
    assert (f[0]["bbox"][3] - f[0]["bbox"][1]) > 35


# 3. page-number-only variation -> same footer common_region_id across pages
def test_page_number_variable_same_group():
    det = _detect("core_multipage_table_cont")           # footer "Confidential — N" per page
    ids = {_commons(det, p, "footer")[0]["common_region_id"]
           for p in range(1, len(det["pages"]) + 1) if _commons(det, p, "footer")}
    assert len(ids) == 1, ids


# 4. even/odd mirrored header produces per-page bbox without crashing
def test_evenodd_jitter_header_per_page():
    det = _detect("exp_hf_evenodd_mirror_with_jitter")
    for p in range(1, len(det["pages"]) + 1):
        assert _commons(det, p, "header"), f"no header on page {p}"


# 5. jittered header/footer keep one common group id
def test_jitter_same_common_group():
    det = _detect("exp_hf_rule_y_jitter")
    hids = {_commons(det, p, "header")[0]["common_region_id"]
            for p in range(1, len(det["pages"]) + 1) if _commons(det, p, "header")}
    assert len(hids) == 1, hids


# 6. extractable watermark text detected
def test_extractable_watermark_detected():
    det = _detect("exp_wm_license_text_position_jitter")   # "Licensed to ..." rot 0
    wms = [c for p in det["pages"] for c in p["common_regions"] if c["kind"] == "watermark"]
    assert wms, "extractable watermark not detected"
    assert any("Licensed to" in (w.get("text") or "") for w in wms)


# 7. negative ordinary body text is NOT misdetected as header/footer
def test_negative_body_not_common_region():
    det = _detect("neg_plain_text_only")
    for p in det["pages"]:
        assert not [c for c in p["common_regions"] if c["kind"] in ("header", "footer")]


# 8. no-truth guarantee still holds
def test_no_truth_guarantee(tmp_path):
    import fitz
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.insert_textbox(fitz.Rect(48, 18, 564, 40), "Synthetic Running Header", fontsize=9, align=1)
    pdf = tmp_path / "h.pdf"; doc.save(str(pdf)); doc.close()
    assert not (tmp_path / "h.truth.json").exists()
    det = detect_pdf(pdf)
    hdr = [c for c in det["pages"][0]["common_regions"] if c["kind"] == "header"]
    assert hdr and hdr[0]["bbox"][0] == 48 and hdr[0]["bbox"][2] == 564


# 9. D12.5 table identity gains preserved (slow: full frozen compare)
@pytest.mark.slow
@pytest.mark.rtm_integration
def test_table_identity_preserved(capsys, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_detector_on_rtm", ROOT / "picker_cmc_v1" / "tools" / "run_detector_on_rtm.py")
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    cmd = f'{sys.executable} {ROOT / "picker_cmc_v1" / "tools" / "detect_pdf.py"} --pdf {{pdf}} --out {{out}}'
    runner.main(["--rtm-root", str(FROZEN), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = json.loads(capsys.readouterr().out)
    rep = json.loads(Path(js["compare_report_json"]).read_text())
    tbl_bad = sum(1 for c in rep["cases"] for o in c["objects"]
                  if o["status"] in ("missing", "extra") and o.get("kind") == "table")
    assert tbl_bad == 0, f"{tbl_bad} table identity regressions"
    assert js["summary"]["objects_matched"] >= 92
