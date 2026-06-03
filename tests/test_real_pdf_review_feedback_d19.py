"""D19 real-PDF operator feedback loop tests (schema + summary; no detector tuning)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from detector.review_feedback import (  # noqa: E402
    ReviewError, summarize, validate_review,
)

CLI = PKG / "tools" / "summarize_review_feedback.py"

DETECTED = {
    "schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt",
    "coordinate_origin": "top-left", "producer": {"name": "picker_cmc", "version": "dev", "mode": "detector"},
    "cases": [{"case_id": "dp", "pdf": "dp.pdf", "pages": [
        {"page": 1, "common_regions": [],
         "figures": [{"kind": "figure", "index": "3-3", "title": "t", "title_position": "below",
                      "title_body_gap_lines": 0, "caption_region": [0, 0, 1, 1],
                      "body_region": [0, 0, 1, 1], "context_region": [0, 0, 1, 1]}],
         "tables": []},
        {"page": 2, "common_regions": [], "figures": [],
         "tables": [{"kind": "table", "index": "3-1", "title": "t", "table_group_id": "tbl_003_001",
                     "part_index": 1, "is_continuation": False, "continuation_marker": None,
                     "caption_region": [0, 0, 1, 1], "body_region": [0, 0, 1, 1]}]},
    ]}],
}


def _review(objects, missed=None):
    return {"schema_version": "real-pdf-review-v0", "pdf": "dp.pdf", "reviewer": "manual",
            "objects": objects, "missed_objects": missed or []}


# (1) a valid review parses/validates
def test_valid_review_passes():
    r = _review([{"object_id": "figure:3-3:page1", "decision": "accept"},
                 {"object_id": "table:3-1:page2", "decision": "bad_body_region"}])
    assert validate_review(r, DETECTED) == []


# (2) invalid object_id rejected
def test_invalid_object_id_rejected():
    r = _review([{"object_id": "fig_3_3", "decision": "accept"}])
    errs = validate_review(r, DETECTED)
    assert any("invalid object_id" in e for e in errs)


# (3) unknown decision rejected
def test_unknown_decision_rejected():
    r = _review([{"object_id": "figure:3-3:page1", "decision": "looks_fine"}])
    errs = validate_review(r, DETECTED)
    assert any("unknown decision" in e for e in errs)


# object_id not present in the detected manifest is rejected
def test_unknown_object_id_rejected():
    r = _review([{"object_id": "figure:9-9:page1", "decision": "accept"}])
    errs = validate_review(r, DETECTED)
    assert any("not found in detected" in e for e in errs)


# (4) missed_object entry accepted
def test_missed_object_accepted():
    r = _review([{"object_id": "figure:3-3:page1", "decision": "accept"}],
                missed=[{"kind": "table", "page": 2, "index": "3-2", "approximate_region": [1, 2, 3, 4]}])
    assert validate_review(r, DETECTED) == []
    s = summarize(r, DETECTED)
    assert s["missed_objects"] == 1 and s["issues"]["missed_object"] == 1


# (5)(6) summary counts decisions + generates recommended_next_tasks
def test_summary_counts_and_tasks():
    r = _review([
        {"object_id": "figure:3-3:page1", "decision": "accept"},
        {"object_id": "table:3-1:page2", "decision": "bad_body_region",
         "expected_change": {"body_region": [1, 2, 3, 4]}},
    ])
    s = summarize(r, DETECTED)
    assert s["reviewed_objects"] == 2 and s["accepted"] == 1
    assert s["issues"]["bad_body_region"] == 1
    assert any("body_region" in t for t in s["recommended_next_tasks"])


# (7) CLI --json is pure JSON
def test_cli_json_pure(tmp_path):
    review = tmp_path / "rv.json"
    review.write_text(json.dumps(_review([{"object_id": "figure:3-3:page1", "decision": "accept"}])))
    detected = tmp_path / "det.json"; detected.write_text(json.dumps(DETECTED))
    out = tmp_path / "summary.json"
    proc = subprocess.run([sys.executable, str(CLI), "--review", str(review),
                           "--detected", str(detected), "--out", str(out), "--json"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] and payload["accepted"] == 1
    assert json.loads(out.read_text())["ok"]


# CLI structured error on an invalid review
def test_cli_invalid_review_structured_error(tmp_path):
    review = tmp_path / "rv.json"
    review.write_text(json.dumps(_review([{"object_id": "nope", "decision": "accept"}])))
    proc = subprocess.run([sys.executable, str(CLI), "--review", str(review), "--json"],
                          capture_output=True, text=True)
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["error_code"] == "INVALID_REVIEW"


# (8) no real/user PDF is committed as a fixture by these tests
def test_no_user_pdf_committed():
    assert not list((ROOT / "tests").glob("**/*.pdf"))
    assert summarize  # module import side-effect free
