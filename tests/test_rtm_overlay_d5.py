"""D5 validation: compare-result overlay artifact generation (overlay.py).

Builds a tiny real PDF + truth + detected + D4 compare_report in tmp, then
renders overlays. Pixel colors are not asserted; PNG creation, the overlay
manifest contents (which regions/failures were drawn), and coordinate sanity
are. Not the D6 full integration.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
sys.path.insert(0, str(FACTORY_DIR))

from rtm_factory.compare import (  # noqa: E402
    ComparisonConfig,
    InvalidInput,
    compare_cases,
    load_detected_manifest,
    load_truth_cases,
)
from rtm_factory.overlay import OverlayConfig, generate, pt_to_px  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CID = "ov_demo"


def _truth() -> dict:
    return {
        "case_id": CID, "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left",
        "pages": [
            {"page": 1, "width": 612, "height": 792,
             "common_regions": [{"kind": "header", "bbox": [48, 18, 564, 54], "text": "Header"}],
             "figures": [{"kind": "figure", "index": "3.4", "title": "WF",
                          "caption_region": [54, 492, 558, 520], "body_region": [54, 220, 558, 485],
                          "context_region": [48, 210, 564, 530]}],
             "tables": [{"kind": "table", "index": "2.1", "title": "Reg", "table_group_id": "g1",
                         "part_index": 1, "is_continuation": False, "continuation_marker": None,
                         "caption_region": [54, 90, 558, 118], "body_region": [54, 128, 558, 470],
                         "context_region": [48, 82, 564, 478]}]},
            {"page": 2, "width": 612, "height": 792,
             "common_regions": [],
             "figures": [{"kind": "figure", "index": "A.1", "title": "D",
                          "caption_region": [54, 120, 558, 148], "body_region": [54, 160, 558, 430],
                          "context_region": [48, 112, 564, 438]}],
             "tables": []},
        ],
    }


def _make_pdf(path: Path, npages: int) -> None:
    doc = fitz.open()
    for _ in range(npages):
        doc.new_page(width=612, height=792)
    doc.save(str(path))
    doc.close()


def _truth_root(tmp: Path) -> Path:
    root = tmp / "rtm_frozen"
    (root / CID).mkdir(parents=True, exist_ok=True)
    truth = _truth()
    _make_pdf(root / CID / f"{CID}.pdf", len(truth["pages"]))
    (root / "MANIFEST.json").write_text(json.dumps({"schema_version": "rtm-frozen-v0", "cases": [{"case_id": CID}]}), encoding="utf-8")
    (root / CID / f"{CID}.truth.json").write_text(json.dumps(truth), encoding="utf-8")
    return root


def _detected(perturb=None) -> dict:
    t = _truth()
    cases = [{"case_id": CID, "pages": [
        {"page": p["page"], "common_regions": p["common_regions"], "figures": p["figures"], "tables": p["tables"]}
        for p in t["pages"]]}]
    d = {"schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left", "cases": cases}
    if perturb:
        perturb(d)
    return d


def _setup(tmp: Path, detected: dict):
    root = _truth_root(tmp)
    det_path = tmp / "detected.json"
    det_path.write_text(json.dumps(detected), encoding="utf-8")
    truth_cases = load_truth_cases(root)
    det_map = load_detected_manifest(det_path)
    report = compare_cases(truth_cases, det_map, ComparisonConfig())
    rep_path = tmp / "compare_report.json"
    rep_path.write_text(json.dumps(report), encoding="utf-8")
    return root, det_path, rep_path, report


def test_overlay_png_and_manifest_created(tmp_path):
    root, det, rep, _ = _setup(tmp_path, _detected())
    out = tmp_path / "artifacts"
    result = generate(root, det, rep, out, OverlayConfig(all_cases=True))
    assert result["pages_rendered"] == 2
    manifest = json.loads((out / "overlay_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "rtm-overlay-v0"
    assert (out / "index.md").exists()
    for case in manifest["cases"]:
        for p in case["pages"]:
            png = out / p["overlay_png"]
            assert png.read_bytes().startswith(PNG_MAGIC)
            assert p["regions_drawn"] > 0


def test_failures_only_renders_only_failed_page(tmp_path):
    def perturb(d):
        cap = d["cases"][0]["pages"][1]["figures"][0]["caption_region"]  # page 2, beyond tol
        cap[1] += 30
        cap[3] += 30
    root, det, rep, report = _setup(tmp_path, _detected(perturb))
    assert report["summary"]["cases_failed"] == 1
    out = tmp_path / "artifacts"
    result = generate(root, det, rep, out, OverlayConfig(failures_only=True))
    pages = [p["page"] for c in result["cases"] for p in c["pages"]]
    assert pages == [2]
    page2 = result["cases"][0]["pages"][0]
    assert page2["failure_png"] is not None
    assert page2["failures_drawn"] > 0
    assert (out / page2["failure_png"]).read_bytes().startswith(PNG_MAGIC)


def test_missing_and_extra_reflected_in_manifest(tmp_path):
    def perturb(d):
        d["cases"][0]["pages"][0]["figures"] = []  # missing figure 3.4
        extra = copy.deepcopy(_truth()["pages"][0]["tables"][0])
        extra["index"] = "9.9"
        extra["table_group_id"] = "gX"
        d["cases"][0]["pages"][0]["tables"].append(extra)  # extra table
    root, det, rep, report = _setup(tmp_path, _detected(perturb))
    assert report["summary"]["objects_missing"] >= 1
    assert report["summary"]["objects_extra"] >= 1
    out = tmp_path / "artifacts"
    result = generate(root, det, rep, out, OverlayConfig())
    p1 = next(p for c in result["cases"] for p in c["pages"] if p["page"] == 1)
    assert p1["failures_drawn"] > 0
    assert (out / p1["failure_png"]).read_bytes().startswith(PNG_MAGIC)


def test_coordinate_transform_within_bounds(tmp_path):
    scale = 1.5
    w, h = 612, 792
    px = pt_to_px([48, 18, 564, 54], scale)
    assert px == [72.0, 27.0, 846.0, 81.0]
    assert 0 <= px[0] <= w * scale and 0 <= px[2] <= w * scale
    assert 0 <= px[1] <= h * scale and 0 <= px[3] <= h * scale


def test_all_pass_without_all_flag_renders_nothing(tmp_path):
    root, det, rep, report = _setup(tmp_path, _detected())
    assert report["summary"]["cases_failed"] == 0
    out = tmp_path / "artifacts"
    result = generate(root, det, rep, out, OverlayConfig())  # no --all, no failures
    assert result["pages_rendered"] == 0
    assert (out / "index.md").exists()


def test_wrong_schema_version_invalid(tmp_path):
    det = _detected()
    det["schema_version"] = "wrong-version"
    root = _truth_root(tmp_path)
    det_path = tmp_path / "detected.json"
    det_path.write_text(json.dumps(det), encoding="utf-8")
    rep_path = tmp_path / "compare_report.json"
    rep_path.write_text(json.dumps({"summary": {}, "failures": [], "cases": []}), encoding="utf-8")
    with pytest.raises(InvalidInput):
        generate(root, det_path, rep_path, tmp_path / "artifacts", OverlayConfig())
