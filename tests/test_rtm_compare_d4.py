"""D4 validation: detector-vs-truth comparison harness (compare.py).

No real detector is needed: truth is read, a detected manifest is synthesized
from it, and individual values are perturbed to exercise pass/fail paths.
This is NOT the D6 full pytest integration.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
sys.path.insert(0, str(FACTORY_DIR))

from rtm_factory.compare import (  # noqa: E402
    ComparisonConfig,
    InvalidInput,
    ToleranceProfile,
    compare_cases,
    load_detected_manifest,
    load_truth_cases,
    write_compare_report,
)

CID = "core_demo"


def _truth_case() -> dict:
    return {
        "case_id": CID,
        "coordinate_unit": "pdf_pt",
        "coordinate_origin": "top-left",
        "pages": [{
            "page": 1, "width": 612, "height": 792,
            "common_regions": [{"kind": "header", "bbox": [48, 18, 564, 54], "text": "Header"}],
            "figures": [{
                "kind": "figure", "index": "3.4", "title": "Waveform",
                "caption_region": [54, 492, 558, 520],
                "body_region": [54, 220, 558, 485],
                "context_region": [48, 210, 564, 530],
            }],
            "tables": [{
                "kind": "table", "index": "2.1", "title": "Register map",
                "table_group_id": "g1", "part_index": 1,
                "is_continuation": False, "continuation_marker": None,
                "caption_region": [54, 90, 558, 118],
                "body_region": [54, 128, 558, 710],
                "context_region": [48, 82, 564, 718],
            }],
        }],
    }


def _write_truth_root(tmp_path: Path) -> Path:
    root = tmp_path / "rtm_truth"
    root.mkdir(exist_ok=True)
    truth = _truth_case()
    (root / "MANIFEST.json").write_text(json.dumps({"schema_version": "rtm-gallery-v0", "cases": [{"case_id": CID}]}), encoding="utf-8")
    (root / CID).mkdir(exist_ok=True)
    (root / CID / f"{CID}.truth.json").write_text(json.dumps(truth), encoding="utf-8")
    return root


def _detected_from_truth() -> dict:
    t = _truth_case()
    page = t["pages"][0]
    return {
        "schema_version": "detector-output-v0",
        "coordinate_unit": "pdf_pt",
        "coordinate_origin": "top-left",
        "cases": [{
            "case_id": CID,
            "pages": [{
                "page": 1,
                "common_regions": copy.deepcopy(page["common_regions"]),
                "figures": copy.deepcopy(page["figures"]),
                "tables": copy.deepcopy(page["tables"]),
            }],
        }],
    }


def _run(tmp_path: Path, detected: dict, **cfg) -> dict:
    root = _write_truth_root(tmp_path)
    det_path = tmp_path / "detected.json"
    det_path.write_text(json.dumps(detected), encoding="utf-8")
    truth_cases = load_truth_cases(root)
    det_map = load_detected_manifest(det_path)
    config = ComparisonConfig(tolerance=ToleranceProfile.named(cfg.get("profile", "strict")),
                              allow_extra=cfg.get("allow_extra", False))
    return compare_cases(truth_cases, det_map, config)


def test_identical_passes(tmp_path):
    rep = _run(tmp_path, _detected_from_truth())
    assert rep["summary"]["cases_failed"] == 0
    assert rep["summary"]["objects_matched"] == 3
    assert rep["summary"]["regions_failed"] == 0


def test_y_shift_beyond_tolerance_fails(tmp_path):
    det = _detected_from_truth()
    # caption_region y tol = 5; shift y0/y1 by 9 → fail
    cap = det["cases"][0]["pages"][0]["figures"][0]["caption_region"]
    cap[1] += 9; cap[3] += 9
    rep = _run(tmp_path, det)
    assert rep["summary"]["cases_failed"] == 1
    assert rep["summary"]["regions_failed"] >= 1


def test_x_shift_within_tolerance_passes(tmp_path):
    det = _detected_from_truth()
    # caption_region x tol = 8; shift x by 3 → pass
    cap = det["cases"][0]["pages"][0]["figures"][0]["caption_region"]
    cap[0] += 3; cap[2] -= 3
    rep = _run(tmp_path, det)
    assert rep["summary"]["cases_failed"] == 0


def test_missing_object_fails(tmp_path):
    for kind in ("figures", "tables", "common_regions"):
        det = _detected_from_truth()
        det["cases"][0]["pages"][0][kind] = []
        rep = _run(tmp_path, det)
        assert rep["summary"]["cases_failed"] == 1, kind
        assert rep["summary"]["objects_missing"] >= 1, kind


def test_extra_object_fails_by_default(tmp_path):
    det = _detected_from_truth()
    extra = copy.deepcopy(det["cases"][0]["pages"][0]["figures"][0])
    extra["index"] = "9.9"
    det["cases"][0]["pages"][0]["figures"].append(extra)
    rep = _run(tmp_path, det)
    assert rep["summary"]["objects_extra"] == 1
    assert rep["summary"]["cases_failed"] == 1


def test_extra_object_allowed_with_flag(tmp_path):
    det = _detected_from_truth()
    extra = copy.deepcopy(det["cases"][0]["pages"][0]["figures"][0])
    extra["index"] = "9.9"
    det["cases"][0]["pages"][0]["figures"].append(extra)
    rep = _run(tmp_path, det, allow_extra=True)
    assert rep["summary"]["objects_extra"] == 1
    assert rep["summary"]["cases_failed"] == 0


def test_wrong_table_group_id_fails(tmp_path):
    det = _detected_from_truth()
    det["cases"][0]["pages"][0]["tables"][0]["table_group_id"] = "WRONG"
    rep = _run(tmp_path, det)
    # group is part of the identity key → truth object missing + detected extra
    assert rep["summary"]["cases_failed"] == 1
    assert rep["summary"]["objects_missing"] >= 1


def test_wrong_continuation_marker_fails(tmp_path):
    det = _detected_from_truth()
    det["cases"][0]["pages"][0]["tables"][0]["is_continuation"] = True
    det["cases"][0]["pages"][0]["tables"][0]["continuation_marker"] = "(cont)"
    rep = _run(tmp_path, det)
    assert rep["summary"]["cases_failed"] == 1
    fail = rep["failures"][0]
    assert any(not f["passed"] for f in fail["fields"])


def test_coordinate_mismatch_is_invalid_input(tmp_path):
    det = _detected_from_truth()
    det["coordinate_origin"] = "bottom-left"
    det_path = tmp_path / "detected.json"
    det_path.write_text(json.dumps(det), encoding="utf-8")
    with pytest.raises(InvalidInput):
        load_detected_manifest(det_path)


def test_missing_schema_version_is_invalid(tmp_path):
    det = _detected_from_truth()
    del det["schema_version"]
    det_path = tmp_path / "detected.json"
    det_path.write_text(json.dumps(det), encoding="utf-8")
    with pytest.raises(InvalidInput):
        load_detected_manifest(det_path)


def test_wrong_schema_version_is_invalid(tmp_path):
    det = _detected_from_truth()
    det["schema_version"] = "wrong-version"
    det_path = tmp_path / "detected.json"
    det_path.write_text(json.dumps(det), encoding="utf-8")
    with pytest.raises(InvalidInput):
        load_detected_manifest(det_path)


def test_report_files_created(tmp_path):
    rep = _run(tmp_path, _detected_from_truth())
    json_path, md_path = write_compare_report(rep, tmp_path / "artifacts")
    assert json_path.exists() and md_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert "summary" in loaded and "failures" in loaded and "cases" in loaded
    assert "comparison report" in md_path.read_text(encoding="utf-8").lower()
