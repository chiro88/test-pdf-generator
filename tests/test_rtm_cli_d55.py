"""D5.5 validation: unified RTM CLI usability layer (rtm_factory.cli).

Drives cli.main(argv) in-process and asserts JSON output, exit codes, and
structured error_codes. Not the D6 full integration.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
sys.path.insert(0, str(FACTORY_DIR))

from rtm_factory.cli import main  # noqa: E402

CID = "cli_demo"


def run_json(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)  # asserts stdout is pure JSON


# --- small synthetic truth-root + detected for compare/overlay ---------------
def _truth():
    return {
        "case_id": CID, "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left",
        "pages": [{"page": 1, "width": 612, "height": 792,
                   "common_regions": [{"kind": "header", "bbox": [48, 18, 564, 54], "text": "H"}],
                   "figures": [{"kind": "figure", "index": "3.4", "title": "t",
                                "caption_region": [54, 492, 558, 520], "body_region": [54, 220, 558, 485],
                                "context_region": [48, 210, 564, 530]}],
                   "tables": []}],
    }


def _make_truth_root(tmp):
    import fitz
    root = tmp / "rtm_frozen"
    (root / CID).mkdir(parents=True)
    doc = fitz.open(); doc.new_page(width=612, height=792); doc.save(str(root / CID / f"{CID}.pdf")); doc.close()
    (root / "MANIFEST.json").write_text(json.dumps({"schema_version": "rtm-frozen-v0", "cases": [{"case_id": CID}]}))
    (root / CID / f"{CID}.truth.json").write_text(json.dumps(_truth()))
    return root


def _make_detected(tmp):
    p = _truth()["pages"][0]
    det = {"schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left",
           "cases": [{"case_id": CID, "pages": [{"page": 1, "common_regions": p["common_regions"],
                                                 "figures": p["figures"], "tables": p["tables"]}]}]}
    path = tmp / "detected.json"
    path.write_text(json.dumps(det))
    return path


def test_list_scenarios_json(capsys):
    code, js = run_json(capsys, ["list-scenarios", "--json"])
    assert code == 0 and js["ok"] is True
    ids = [s["case_id"] for s in js["scenarios"]]
    assert "core_figure_caption_bottom" in ids


def test_list_templates_json(capsys):
    code, js = run_json(capsys, ["list-templates", "--json"])
    assert code == 0 and js["ok"] is True
    t = js["templates"]
    assert "waveform" in t["figure_body"] and t["watermark"] and t["table_caption"]


def test_generate_json(capsys, tmp_path):
    out = tmp_path / "rtm_gallery"
    code, js = run_json(capsys, ["generate", "--out", str(out), "--json"])
    assert code == 0 and js["ok"] is True
    assert Path(js["manifest"]).exists() and Path(js["index"]).exists()
    assert js["case_count"] >= 30


def test_generate_case_json(capsys, tmp_path):
    out = tmp_path / "case"
    code, js = run_json(capsys, ["generate-case", "--case-id", "core_figure_caption_bottom", "--out", str(out), "--json"])
    assert code == 0 and js["ok"] is True
    assert Path(js["pdf"]).exists() and Path(js["truth"]).exists()
    assert js["previews"] and Path(js["previews"][0]).read_bytes().startswith(b"\x89PNG")


def test_validate_scenario_ok(capsys, tmp_path):
    scen = tmp_path / "ok.yaml"
    scen.write_text(
        "case_id: cli_ok\n"
        "page: {size: letter, orientation: portrait, columns: 1, page_count: 1}\n"
        "figures:\n"
        "  - index: '3.4'\n"
        "    title: demo\n"
        "    caption_region: [54, 492, 558, 520]\n"
        "    body_region: [54, 220, 558, 485]\n"
        "    body_template: waveform\n"
        "    alias: Figure\n"
        "    caption_position: below\n"
        "    page: 1\n"
    )
    code, js = run_json(capsys, ["validate-scenario", str(scen), "--json"])
    assert code == 0 and js["ok"] is True and js["valid"] is True and js["case_id"] == "cli_ok"


def test_validate_scenario_unknown_template(capsys, tmp_path):
    scen = tmp_path / "bad.yaml"
    scen.write_text(
        "case_id: cli_bad\n"
        "page: {size: letter, page_count: 1}\n"
        "figures:\n"
        "  - index: '1.1'\n"
        "    title: x\n"
        "    caption_region: [54, 100, 558, 126]\n"
        "    body_region: [54, 140, 558, 400]\n"
        "    body_template: wavefrom_typo\n"
    )
    code, js = run_json(capsys, ["validate-scenario", str(scen), "--json"])
    assert code == 2 and js["ok"] is False
    assert js["error_code"] == "SCENARIO_UNKNOWN_TEMPLATE"
    assert js["field"] == "figures[0].body_template"
    assert "waveform" in js["allowed_values"]


def test_validate_scenario_out_of_bounds(capsys, tmp_path):
    scen = tmp_path / "oob.yaml"
    scen.write_text(
        "case_id: cli_oob\n"
        "page: {size: letter, page_count: 1}\n"
        "figures:\n"
        "  - index: '1.1'\n"
        "    title: x\n"
        "    caption_region: [54, 100, 800, 126]\n"  # x1=800 > 612
        "    body_region: [54, 140, 558, 400]\n"
        "    body_template: waveform\n"
    )
    code, js = run_json(capsys, ["validate-scenario", str(scen), "--json"])
    assert code == 2 and js["error_code"] == "SCENARIO_OUT_OF_PAGE_BOUNDS"


def test_self_check_json(capsys, tmp_path):
    out = tmp_path / "rtm_gallery"
    run_json(capsys, ["generate", "--out", str(out), "--json"])
    code, js = run_json(capsys, ["self-check", "--gallery", str(out), "--json"])
    assert code == 0 and js["ok"] is True and js["passed"] is True
    assert js["coverage"]["missing"] == [] and js["coverage"]["below_min"] == []
    assert js["text_overlap"]["checked"] >= 1


def test_compare_json_preserves_pass(capsys, tmp_path):
    root = _make_truth_root(tmp_path)
    det = _make_detected(tmp_path)
    code, js = run_json(capsys, ["compare", "--truth-root", str(root), "--detected", str(det),
                                 "--out", str(tmp_path / "cmp"), "--json"])
    assert code == 0 and js["ok"] is True and js["passed"] is True
    assert Path(js["report_json"]).exists() and Path(js["report_md"]).exists()


def test_overlay_json(capsys, tmp_path):
    root = _make_truth_root(tmp_path)
    det = _make_detected(tmp_path)
    run_json(capsys, ["compare", "--truth-root", str(root), "--detected", str(det),
                      "--out", str(tmp_path / "cmp"), "--json"])
    code, js = run_json(capsys, ["overlay", "--truth-root", str(root), "--detected", str(det),
                                 "--compare-report", str(tmp_path / "cmp" / "compare_report.json"),
                                 "--out", str(tmp_path / "ov"), "--all", "--json"])
    assert code == 0 and js["ok"] is True
    assert Path(js["manifest"]).exists() and Path(js["index"]).exists()


def test_invalid_input_emits_pure_json(capsys):
    # unknown built-in case_id with --json must still print ONLY valid JSON
    code, js = run_json(capsys, ["generate-case", "--case-id", "no_such_case", "--out", "/tmp/none", "--json"])
    assert code == 2 and js["ok"] is False and js["error_code"] == "INVALID_INPUT"
