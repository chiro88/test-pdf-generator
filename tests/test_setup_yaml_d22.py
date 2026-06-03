"""D22 setup-yaml-v0 contract tests (template / parse / validate / error codes / runner)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import fitz
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from setup.errors import SetupError  # noqa: E402
from setup.loader import load_setup  # noqa: E402
from setup.template import render_template  # noqa: E402
from setup.validator import validate_setup  # noqa: E402
from detector_output.validator import validate_manifest as validate_detector  # noqa: E402

RUN = PKG / "tools" / "run_detector_with_setup.py"


def _write_setup(tmp_path, **over):
    cfg = yaml.safe_load(render_template())
    cfg["project"]["name"] = "test"
    cfg["input"]["pdf_path"] = str(tmp_path / "in.pdf")
    cfg["output"]["artifact_dir"] = str(tmp_path / "out")
    cfg["output"]["save_manifest_path"] = str(tmp_path / "out" / "save.json")
    for k, v in over.items():
        cfg[k[0]][k[1]] = v if len(k) == 2 else None
    p = tmp_path / "setup.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p, cfg


# (1) template generation includes comments + placeholders
def test_template_has_comments_and_placeholders():
    t = render_template()
    assert t.lstrip().startswith("#") and "CHANGE_ME" in t and "schema_version: setup-yaml-v0" in t


# (2) a valid setup YAML parses + validates
def test_valid_setup_validates(tmp_path):
    p, _ = _write_setup(tmp_path)
    cfg = validate_setup(load_setup(p))
    assert cfg["schema_version"] == "setup-yaml-v0"


# (3) missing pdf_path -> SETUP_MISSING_FIELD
def test_missing_pdf_path(tmp_path):
    cfg = yaml.safe_load(render_template())
    cfg["project"]["name"] = "x"
    del cfg["input"]["pdf_path"]
    p = tmp_path / "s.yaml"; p.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SetupError) as e:
        validate_setup(load_setup(p))
    assert e.value.code == "SETUP_MISSING_FIELD" and e.value.field == "input.pdf_path"


# (4) missing setup file -> SETUP_FILE_NOT_FOUND
def test_missing_file(tmp_path):
    with pytest.raises(SetupError) as e:
        load_setup(tmp_path / "nope.yaml")
    assert e.value.code == "SETUP_FILE_NOT_FOUND"


# (5) unreadable / invalid YAML -> SETUP_FILE_UNREADABLE
def test_bad_yaml(tmp_path):
    p = tmp_path / "bad.yaml"; p.write_text("name: [unterminated\n: : :")
    with pytest.raises(SetupError) as e:
        load_setup(p)
    assert e.value.code == "SETUP_FILE_UNREADABLE"


# (6) CHANGE_ME placeholder -> SETUP_PLACEHOLDER_UNRESOLVED
def test_placeholder_unresolved(tmp_path):
    p = tmp_path / "t.yaml"; p.write_text(render_template())   # unedited template
    with pytest.raises(SetupError) as e:
        validate_setup(load_setup(p))
    assert e.value.code == "SETUP_PLACEHOLDER_UNRESOLVED"


# (7) invalid detector_profile -> SETUP_UNKNOWN_DETECTOR
def test_invalid_detector_profile(tmp_path):
    p, cfg = _write_setup(tmp_path)
    cfg["advanced_fine_tuning"]["detector_profile"] = "magic"
    p.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SetupError) as e:
        validate_setup(load_setup(p))
    assert e.value.code == "SETUP_UNKNOWN_DETECTOR"


# bad page range -> SETUP_BAD_PAGE_RANGE
def test_bad_page_range(tmp_path):
    p, cfg = _write_setup(tmp_path)
    cfg["input"]["page_range"] = "5-2"
    p.write_text(yaml.safe_dump(cfg))
    with pytest.raises(SetupError) as e:
        validate_setup(load_setup(p))
    assert e.value.code == "SETUP_BAD_PAGE_RANGE"


# (8) run_detector_with_setup emits a valid detector-output-v0 manifest
def test_runner_emits_detector_output(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    (tmp_path / "in.pdf").parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(tmp_path / "in.pdf")); doc.close()
    p, cfg = _write_setup(tmp_path)
    proc = subprocess.run([sys.executable, str(RUN), "--setup", str(p), "--json"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    manifest = json.loads(Path(out["detector_manifest"]).read_text())
    assert validate_detector(manifest) == []
    assert out["figures"] >= 1
