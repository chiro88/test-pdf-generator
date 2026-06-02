"""D6 CLI subprocess gate: exercise rtm_cli.py the way an agent actually would.

In-process main() coverage lives in test_rtm_cli_d55.py; here we spawn real
subprocesses to confirm the entrypoint, --json stdout contract, and exit codes
hold end-to-end (including argparse-level errors).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"

pytestmark = [pytest.mark.rtm_integration, pytest.mark.slow]


def run_cli(*args):
    proc = subprocess.run([sys.executable, "rtm_cli.py", *args], cwd=FACTORY_DIR,
                          text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def run_json(*args):
    code, out, err = run_cli(*args)
    return code, json.loads(out)  # asserts stdout is pure JSON


def _synth_detected(gallery_root: Path) -> dict:
    manifest = json.loads((gallery_root / "MANIFEST.json").read_text(encoding="utf-8"))
    cases = []
    for entry in manifest["cases"]:
        cid = entry["case_id"]
        truth = json.loads((gallery_root / cid / f"{cid}.truth.json").read_text(encoding="utf-8"))
        pages = [{
            "page": p["page"],
            "common_regions": [{k: r[k] for k in ("kind", "bbox", "text") if k in r} for r in p["common_regions"]],
            "figures": p["figures"], "tables": p["tables"],
        } for p in truth["pages"]]
        cases.append({"case_id": cid, "pages": pages})
    return {"schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt",
            "coordinate_origin": "top-left", "cases": cases}


def test_list_scenarios_subprocess():
    code, js = run_json("list-scenarios", "--json")
    assert code == 0 and js["ok"] is True
    assert any(s["case_id"] == "core_figure_caption_bottom" for s in js["scenarios"])


def test_generate_and_self_check_and_compare_overlay_subprocess(tmp_path):
    gal = tmp_path / "rtm_gallery"
    code, js = run_json("generate", "--out", str(gal), "--json")
    assert code == 0 and js["ok"] and Path(js["manifest"]).exists()

    code, js = run_json("generate-case", "--case-id", "core_figure_caption_bottom",
                        "--out", str(tmp_path / "case"), "--json")
    assert code == 0 and Path(js["pdf"]).exists()

    code, js = run_json("self-check", "--gallery", str(gal), "--json")
    assert code == 0 and js["passed"] is True and js["coverage"]["missing"] == []

    det = tmp_path / "detected.json"
    det.write_text(json.dumps(_synth_detected(gal)), encoding="utf-8")
    cmp_out = tmp_path / "cmp"
    code, js = run_json("compare", "--truth-root", str(gal), "--detected", str(det),
                        "--out", str(cmp_out), "--json")
    assert code == 0 and js["passed"] is True

    code, js = run_json("overlay", "--truth-root", str(gal), "--detected", str(det),
                        "--compare-report", str(cmp_out / "compare_report.json"),
                        "--out", str(tmp_path / "ov"), "--all", "--json")
    assert code == 0 and Path(js["manifest"]).exists()


def test_argparse_missing_args_is_json(tmp_path):
    code, js = run_json("compare", "--json")
    assert code == 2 and js["ok"] is False and js["error_code"] == "INVALID_INPUT"


def test_unknown_command_is_json():
    code, js = run_json("no-such-command", "--json")
    assert code == 2 and js["ok"] is False and js["error_code"] == "INVALID_INPUT"
