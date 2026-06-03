"""D28 product end-to-end smoke (synthetic PDF): the whole flow in one test."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
FROZEN = PKG / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402

_spec = importlib.util.spec_from_file_location("e2e", PKG / "tools" / "run_product_e2e_smoke.py")
_e2e = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_e2e)


def _make_pdf(path: Path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    pg.insert_text((100, 300), "Table 1 Measurements", fontsize=10)
    for i in range(4):
        pg.insert_text((100, 320 + i * 16), f"Row {i} value {i}", fontsize=9)
    doc.save(str(path)); doc.close()


def test_product_e2e_all_stages(tmp_path):
    _make_pdf(tmp_path / "in.pdf")
    summary = _e2e.run_e2e(tmp_path / "in.pdf", tmp_path / "work")
    assert summary["ok"], summary["stages"]
    for stage, ok in summary["stages"].items():
        assert ok, f"stage failed: {stage}"


def test_product_e2e_artifacts_and_provenance(tmp_path):
    _make_pdf(tmp_path / "in.pdf")
    s = _e2e.run_e2e(tmp_path / "in.pdf", tmp_path / "work")
    a = s["artifacts"]
    # all key artifacts exist
    assert Path(a["detected_manifest"]).exists()
    assert Path(a["editor_save_manifest"]).exists()
    assert (Path(a["edited_review"]) / "summary.json").exists()
    assert Path(a["package_manifest"]).exists()
    assert Path(a["objects_jsonl"]).exists()
    # package provenance points at the editor manifest, not the detector output
    assert s["source_editor_manifest"].rsplit("/", 1)[-1] != "detected_manifest.json"
    # the edit persisted (after != before)
    assert s["bbox_after"] != s["bbox_before"]


def test_product_e2e_cli(tmp_path):
    import subprocess
    _make_pdf(tmp_path / "in.pdf")
    cli = PKG / "tools" / "run_product_e2e_smoke.py"
    proc = subprocess.run([sys.executable, str(cli), "--pdf", str(tmp_path / "in.pdf"),
                           "--workdir", str(tmp_path / "work"), "--json"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["ok"] is True


def test_rtm_regression_unchanged(tmp_path):
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4))
