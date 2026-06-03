"""D22 editor-save-manifest-v0 contract tests (build / edit log / validate)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from editor_manifest import writer  # noqa: E402
from editor_manifest.validator import validate_manifest  # noqa: E402

DET = {
    "schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt",
    "coordinate_origin": "top-left", "producer": {"name": "picker_cmc", "version": "dev", "mode": "detector"},
    "cases": [{"case_id": "c", "pdf": "x.pdf", "pages": [
        {"page": 1, "common_regions": [],
         "figures": [{"kind": "figure", "index": "3-3", "title": "t", "title_position": "below",
                      "title_body_gap_lines": 0, "caption_region": [0, 0, 1, 1],
                      "body_region": [10, 10, 20, 20], "context_region": [0, 0, 1, 1]}],
         "tables": []}]}],
}


# (9) validator accepts a valid manifest (built from a detector proposal)
def test_valid_save_manifest_accepted():
    m = writer.build_initial(DET, source_pdf="x.pdf", source_detector_manifest="d.json")
    assert validate_manifest(m) == []
    assert m["pages"][0]["figures"][0]["index"] == "3-3" and m["edits"] == []


# (10) validator rejects a wrong coordinate_origin/unit
def test_wrong_coordinate_rejected():
    m = writer.build_initial(DET, source_pdf="x.pdf", source_detector_manifest="d.json")
    m["coordinate_origin"] = "bottom-left"
    errs = validate_manifest(m)
    assert any("coordinate_origin" in e for e in errs)
    m2 = writer.build_initial(DET, source_pdf="x.pdf", source_detector_manifest="d.json")
    m2["coordinate_unit"] = "px"
    assert any("coordinate_unit" in e for e in validate_manifest(m2))


# an operator bbox edit is applied in-place AND recorded in the append-only log
def test_bbox_edit_logged_and_applied():
    m = writer.build_initial(DET, source_pdf="x.pdf", source_detector_manifest="d.json")
    writer.apply_bbox_edit(m, "figure:3-3:page1", "body_region", [11, 12, 33, 44])
    assert validate_manifest(m) == []
    assert m["pages"][0]["figures"][0]["body_region"] == [11, 12, 33, 44]   # in-place
    e = m["edits"][0]
    assert e["operation"] == "update_bbox" and e["before"] == [10, 10, 20, 20] and e["after"] == [11, 12, 33, 44]


# a malformed edit (bad operation / missing after) is rejected
def test_bad_edit_rejected():
    m = writer.build_initial(DET, source_pdf="x.pdf", source_detector_manifest="d.json")
    m["edits"].append({"object_id": "figure:3-3:page1", "operation": "frobnicate"})
    assert any("operation" in e for e in validate_manifest(m))
