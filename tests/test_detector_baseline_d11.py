"""D11 no-truth detector baseline tests.

D11 green = the real detector runs on PDFs WITHOUT truth, emits a valid
detector-output-v0 manifest, and its failures are quantified by compare/overlay.
It is NOT a correctness proof (body/context bbox accuracy is allowed to be low).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"

from detector.pipeline import detect_pdf  # noqa: E402
from detector.title_patterns import match_caption  # noqa: E402
from detector_output.validator import validate_manifest  # noqa: E402
from detector_output import writer  # noqa: E402


def _runner():
    spec = importlib.util.spec_from_file_location(
        "run_detector_on_rtm", ROOT / "picker_cmc_v1" / "tools" / "run_detector_on_rtm.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def _figure_pdf(path: Path):
    doc = fitz.open(); page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(54, 120, 558, 300), width=1)          # body
    page.insert_textbox(fitz.Rect(54, 320, 558, 338), "Figure 1-1. Synthetic block", fontsize=9)  # caption below
    doc.save(str(path)); doc.close()


# 4. title pattern: aliases + index styles
@pytest.mark.parametrize("text,kind,index", [
    ("Figure 3.4. Waveform timing", "figure", "3.4"),
    ("Fig. A.1. Reset path", "figure", "A.1"),
    ("FIGURE 2-7. Datapath", "figure", "2-7"),
    ("Figure 12. Output", "figure", "12"),
    ("Table 3-1. Bus map", "table", "3-1"),
    ("Table 2.1. Register map (cont)", "table", "2.1"),
])
def test_title_patterns_detect(text, kind, index):
    m = match_caption(text)
    assert m is not None and m[0] == kind and m[1] == index


# 5. negatives must NOT produce anchors
@pytest.mark.parametrize("text", [
    "Figure of merit is defined as the ratio of useful output to input power.",
    "For configuration details, see Table above in the previous section.",
    "Figure 3.4 is referenced for historical context only; the diagram is not reproduced.",
    "Table 2.1 describes the legacy configuration in an earlier revision; not reproduced.",
])
def test_negative_text_not_a_caption(text):
    assert match_caption(text) is None


def test_detector_emits_valid_output_and_no_truth(tmp_path):
    # 1 + 2 + 3: detect on a PDF with NO truth.json beside it -> valid manifest
    pdf = tmp_path / "fig.pdf"
    _figure_pdf(pdf)
    assert not (tmp_path / "fig.truth.json").exists()
    result = detect_pdf(pdf)  # signature only takes the PDF
    assert result["pages"][0]["figures"], "expected one figure anchor"
    fig = result["pages"][0]["figures"][0]
    assert fig["index"] == "1-1" and fig["title_position"] == "below"
    manifest = writer.build_manifest([writer.case("fig", "fig.pdf", result["pages"])])
    assert validate_manifest(manifest) == []


def test_negative_pdf_emits_no_anchor(tmp_path):
    doc = fitz.open(); page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(70, 160, 540, 230),
                        "Figure 3.4 is referenced for historical context only; the diagram is not reproduced.", fontsize=10)
    pdf = tmp_path / "neg.pdf"; doc.save(str(pdf)); doc.close()
    result = detect_pdf(pdf)
    assert all(not p["figures"] and not p["tables"] for p in result["pages"])


@pytest.mark.slow
@pytest.mark.rtm_integration
def test_runner_with_real_detector_over_frozen(capsys, tmp_path):
    assert FROZEN.exists()
    cmd = f'{sys.executable} {ROOT / "picker_cmc_v1" / "tools" / "detect_pdf.py"} --pdf {{pdf}} --out {{out}}'
    code = _runner().main(["--rtm-root", str(FROZEN), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = json.loads(capsys.readouterr().out)
    assert js["ok"] is True and js["producer_mode"] == "detector"
    assert js["case_count"] == 49
    # baseline: real detector won't pass everything; the path must produce all artifacts.
    assert Path(js["detected_manifest"]).exists()
    assert Path(js["compare_report_json"]).exists() and Path(js["compare_report_md"]).exists()
    # detector output is contract-valid (runner validates before compare)
    manifest = json.loads(Path(js["detected_manifest"]).read_text())
    assert validate_manifest(manifest) == []
    if not js["compare_passed"]:
        assert code == 1 and js["overlay"] is not None and Path(js["overlay"]["index"]).exists()


@pytest.mark.slow
@pytest.mark.rtm_integration
def test_anchor_recall_and_no_negative_fp():
    """Baseline metric: >=70% figure/table anchor recall, 0 negative false positives.
    Truth is read here for EVALUATION only — never by the detector."""
    manifest = json.loads((FROZEN / "MANIFEST.json").read_text())
    negatives = {"neg_plain_text_only", "neg_false_figure_of_merit", "neg_false_see_table_above",
                 "neg_caption_reference_only", "neg_false_table_reference", "neg_weak_partial_header"}
    expected = matched = neg_fp = 0
    for entry in manifest["cases"]:
        cid = entry["case_id"]
        det = detect_pdf(FROZEN / cid / f"{cid}.pdf")
        truth = json.loads((FROZEN / cid / f"{cid}.truth.json").read_text())  # evaluation only
        tf = {(p["page"], f["index"]) for p in truth["pages"] for f in p.get("figures", [])}
        tt = {(p["page"], t["index"]) for p in truth["pages"] for t in p.get("tables", [])}
        df = {(p["page"], f["index"]) for p in det["pages"] for f in p["figures"]}
        dt = {(p["page"], t["index"]) for p in det["pages"] for t in p["tables"]}
        expected += len(tf) + len(tt)
        matched += len(tf & df) + len(tt & dt)
        if cid in negatives:
            neg_fp += len(df) + len(dt)
    recall = matched / max(1, expected)
    assert recall >= 0.70, f"anchor recall {recall:.0%} < 70%"
    assert neg_fp == 0, f"{neg_fp} negative false-positive anchors"
