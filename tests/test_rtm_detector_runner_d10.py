"""D10 integration-path tests: run_detector_on_rtm runner.

D10 green = the detector integration PATH works (frozen -> detected manifest ->
compare -> overlay). It is NOT a detector correctness proof; the synthetic /
detector-cmd adapters here are explicit contract tests.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_detector_on_rtm", ROOT / "picker_cmc_v1" / "tools" / "run_detector_on_rtm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load_runner()


def _out(capsys):
    return json.loads(capsys.readouterr().out)


# --- tiny synthetic frozen root + a detector-cmd script ----------------------
DETECTOR_SCRIPT = '''
import json, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--truth"); ap.add_argument("--out"); ap.add_argument("--shift", type=float, default=0.0)
a = ap.parse_args()
t = json.load(open(a.truth)); pages = []
for p in t["pages"]:
    figs = []
    for f in p.get("figures", []):
        cap = list(f["caption_region"]); cap[1] += a.shift; cap[3] += a.shift
        figs.append({"kind":"figure","index":f["index"],"title":f.get("title",""),
                     "caption_region":cap,"body_region":f["body_region"],"context_region":f["context_region"],
                     "title_position":f.get("title_position","below"),"title_body_gap_lines":f.get("title_body_gap_lines",0)})
    pages.append({"page":p["page"],
                  "common_regions":[{"kind":r["kind"],"bbox":r["bbox"]} for r in p.get("common_regions",[])],
                  "figures":figs,"tables":[]})
json.dump({"pages":pages}, open(a.out,"w"))
'''


def _tiny_frozen(tmp: Path) -> Path:
    root = tmp / "rtm_frozen"; (root / "tcase").mkdir(parents=True)
    doc = fitz.open(); doc.new_page(width=612, height=792); doc.save(str(root / "tcase" / "tcase.pdf")); doc.close()
    truth = {"case_id": "tcase", "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left",
             "pages": [{"page": 1, "width": 612, "height": 792,
                        "common_regions": [{"kind": "header", "bbox": [48, 18, 564, 54], "text": "H"}],
                        "figures": [{"kind": "figure", "index": "1-1", "title": "T",
                                     "caption_region": [54, 300, 558, 318], "body_region": [54, 120, 558, 290],
                                     "context_region": [48, 112, 564, 326], "title_position": "below",
                                     "title_body_gap_lines": 1}], "tables": []}]}
    (root / "tcase" / "tcase.truth.json").write_text(json.dumps(truth), encoding="utf-8")
    (root / "MANIFEST.json").write_text(json.dumps(
        {"schema_version": "rtm-frozen-v0", "cases": [{"case_id": "tcase", "pdf": "tcase/tcase.pdf"}]}), encoding="utf-8")
    return root


def test_detector_unavailable_does_not_fake_success(capsys, tmp_path):
    code = runner.main(["--rtm-root", str(_tiny_frozen(tmp_path)), "--out", str(tmp_path / "o"), "--json"])
    js = _out(capsys)
    assert code == 2 and js["ok"] is False and js["error_code"] == "DETECTOR_UNAVAILABLE_OR_INVALID"


@pytest.mark.slow
@pytest.mark.rtm_integration
def test_runner_enumerates_frozen_49_and_synthetic_passes(capsys, tmp_path):
    assert FROZEN.exists(), "rtm_frozen must be promoted first"
    code = runner.main(["--rtm-root", str(FROZEN), "--out", str(tmp_path / "o"), "--synthetic-from-truth", "--json"])
    js = _out(capsys)
    assert js["ok"] is True
    assert js["producer_mode"] == "synthetic-contract-test"
    assert js["case_count"] == 49
    assert js["compare_passed"] is True and code == 0
    assert Path(js["detected_manifest"]).exists() and Path(js["compare_report_json"]).exists()


def test_detector_cmd_perfect_passes(capsys, tmp_path):
    root = _tiny_frozen(tmp_path)
    script = tmp_path / "det.py"; script.write_text(DETECTOR_SCRIPT, encoding="utf-8")
    cmd = f'{sys.executable} {script} --truth {{truth}} --out {{out}} --shift 0'
    code = runner.main(["--rtm-root", str(root), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = _out(capsys)
    assert js["ok"] is True and js["producer_mode"] == "detector"
    assert js["compare_passed"] is True and code == 0


def test_detector_cmd_shift_fails_and_overlay_generated(capsys, tmp_path):
    root = _tiny_frozen(tmp_path)
    script = tmp_path / "det.py"; script.write_text(DETECTOR_SCRIPT, encoding="utf-8")
    cmd = f'{sys.executable} {script} --truth {{truth}} --out {{out}} --shift 30'  # beyond caption y tol (5)
    code = runner.main(["--rtm-root", str(root), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = _out(capsys)
    assert js["ok"] is True
    assert js["compare_passed"] is False and code == 1
    assert js["overlay"] is not None and Path(js["overlay"]["manifest"]).exists()


def test_invalid_detected_manifest_is_rejected(capsys, tmp_path):
    root = _tiny_frozen(tmp_path)
    # detector-cmd that emits a figure missing body_region -> contract invalid
    bad = tmp_path / "bad.py"
    bad.write_text(
        'import json,argparse\n'
        'ap=argparse.ArgumentParser();ap.add_argument("--truth");ap.add_argument("--out");a=ap.parse_args()\n'
        'json.dump({"pages":[{"page":1,"common_regions":[],"figures":[{"kind":"figure","index":"1-1","title":"T",'
        '"caption_region":[1,2,3,4],"context_region":[1,2,3,4],"title_position":"below","title_body_gap_lines":0}],'
        '"tables":[]}]}, open(a.out,"w"))\n', encoding="utf-8")
    cmd = f'{sys.executable} {bad} --truth {{truth}} --out {{out}}'
    code = runner.main(["--rtm-root", str(root), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = _out(capsys)
    assert code == 2 and js["ok"] is False and js["error_code"] == "CONTRACT_INVALID"
