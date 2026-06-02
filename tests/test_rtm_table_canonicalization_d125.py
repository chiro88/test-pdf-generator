"""D12.5: RTM table identity contract correction (canonical group ids) tests.

The fix is on the TRUTH/contract side (PDF-derivable canonical table_group_id) +
a detector continued_from output fix. The detector still never reads truth.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))
sys.path.insert(0, str(ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"))

from detector.pipeline import detect_pdf  # noqa: E402
from detector.table_identity import canonical_group_id as det_canon  # noqa: E402
from detector_output.validator import validate_manifest  # noqa: E402
from detector_output import writer  # noqa: E402
from rtm_factory.sequence import canonical_table_group_id as fac_canon  # noqa: E402


def _frozen_truth(cid):
    return json.loads((FROZEN / cid / f"{cid}.truth.json").read_text())


def _table_groups(cid):
    t = _frozen_truth(cid)
    return [tb["table_group_id"] for p in t["pages"] for tb in p.get("tables", [])]


def test_factory_and_detector_canonical_rule_agree():
    for idx in ["2.1", "10.1", "5-1", "A.1", "13-1"]:
        assert fac_canon(idx) == det_canon(idx)


# 1. sequence table truth group_id canonicalized
def test_sequence_table_truth_canonical():
    assert _table_groups("exp_seq_fig_table") == ["tbl_005_001"]            # index 5-1
    assert _table_groups("exp_seq_table_table") == ["tbl_007_001", "tbl_007_002"]


# 2. gap table truth group_id canonicalized
def test_gap_table_truth_canonical():
    assert _table_groups("exp_gap_tbl_above_g0") == ["tbl_013_001"]         # index 13-1


# 3. same-title independent tables get occurrence-based canonical ids
def test_same_title_occurrence_ids():
    assert _table_groups("core_same_title_tables") == ["tbl_004_002", "tbl_004_003"]


def test_no_noncanonical_group_ids_remain():
    man = json.loads((FROZEN / "MANIFEST.json").read_text())
    for e in man["cases"]:
        for g in _table_groups(e["case_id"]):
            assert "seq" not in g and "gap" not in g and not g.endswith(("_a", "_b")), g


# 4. detector emits continued_from for continuation parts
def test_detector_emits_continued_from():
    det = detect_pdf(FROZEN / "core_multipage_table_cont" / "core_multipage_table_cont.pdf")
    parts = [t for p in det["pages"] for t in p["tables"]]
    assert parts[0]["is_continuation"] is False
    for t in parts[1:]:
        assert t["is_continuation"] is True
        assert t.get("continued_from") == t["table_group_id"]


# 5. validator accepts continued_from on continuation parts
def test_validator_accepts_continued_from():
    tbl = writer.table("2.1", "Reg", "tbl_002_001", [54, 90, 558, 118], [54, 128, 558, 710],
                       part_index=2, is_continuation=True, continuation_marker="(cont)",
                       continued_from="tbl_002_001")
    m = writer.build_manifest([writer.case("c", "c/c.pdf", [writer.page(1, tables=[tbl])])])
    assert validate_manifest(m) == []


# 6. rtm_frozen still 49 cases
def test_frozen_still_49():
    man = json.loads((FROZEN / "MANIFEST.json").read_text())
    assert man["promotion"]["selected_count"] == 49
    assert len(man["cases"]) == 49


# 7. no-truth guarantee still holds
def test_no_truth_guarantee_still_holds(tmp_path):
    import fitz
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(54, 120, 558, 300), width=1)
    pg.insert_textbox(fitz.Rect(54, 320, 558, 360), "Table 7-1. Bus map", fontsize=9)
    pdf = tmp_path / "t.pdf"; doc.save(str(pdf)); doc.close()
    assert not (tmp_path / "t.truth.json").exists()
    det = detect_pdf(pdf)
    assert det["pages"][0]["tables"][0]["table_group_id"] == "tbl_007_001"


# 8. D12.5 compare object matched >= 80 (table identity blocker resolved)
@pytest.mark.slow
@pytest.mark.rtm_integration
def test_compare_object_matched_at_least_80(capsys, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "run_detector_on_rtm", ROOT / "picker_cmc_v1" / "tools" / "run_detector_on_rtm.py")
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    cmd = f'{sys.executable} {ROOT / "picker_cmc_v1" / "tools" / "detect_pdf.py"} --pdf {{pdf}} --out {{out}}'
    runner.main(["--rtm-root", str(FROZEN), "--out", str(tmp_path / "o"), "--detector-cmd", cmd, "--json"])
    js = json.loads(capsys.readouterr().out)
    s = js["summary"]
    assert s["objects_matched"] >= 80, f"objects matched {s['objects_matched']} < 80"
    # table identity blocker resolved
    rep = json.loads(Path(js["compare_report_json"]).read_text())
    tbl_miss = sum(1 for c in rep["cases"] for o in c["objects"] if o["status"] == "missing" and o.get("kind") == "table")
    assert tbl_miss == 0, f"{tbl_miss} table objects still missing"
