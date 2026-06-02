from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
GALLERY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_gallery"


def test_rtm_factory_generate_smoke() -> None:
    result = subprocess.run([sys.executable, "generate.py"], cwd=FACTORY_DIR, text=True, capture_output=True, check=True)
    assert "generated" in result.stdout
    manifest_path = GALLERY_DIR / "MANIFEST.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["coordinate_origin"] == "top-left"
    assert manifest["coordinate_unit"] == "pdf_pt"
    assert len(manifest["cases"]) >= 19


def test_generated_cases_have_required_files() -> None:
    manifest = json.loads((GALLERY_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["cases"]:
        case_dir = GALLERY_DIR / entry["case_id"]
        assert (case_dir / f"{entry['case_id']}.pdf").exists()
        assert (case_dir / f"{entry['case_id']}.truth.json").exists()
        assert (case_dir / f"{entry['case_id']}.notes.md").exists()
        assert (case_dir / f"{entry['case_id']}.p01.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_truth_schema_contract() -> None:
    manifest = json.loads((GALLERY_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    allowed_common = {"header", "footer", "watermark"}
    for entry in manifest["cases"]:
        truth_path = GALLERY_DIR / entry["truth"]
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        assert truth["coordinate_origin"] == "top-left"
        for page in truth["pages"]:
            for region in page["common_regions"]:
                assert region["kind"] in allowed_common
                assert len(region["bbox"]) == 4
            for fig in page["figures"]:
                assert fig["kind"] == "figure"
                assert "caption_region" in fig and "body_region" in fig and "context_region" in fig
            for table in page["tables"]:
                assert table["kind"] == "table"
                assert "caption_region" in table and "body_region" in table
