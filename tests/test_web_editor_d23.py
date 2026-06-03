"""D23 read-only web editor/server tests (synthetic PDF only)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import fitz
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402
from detector_output import writer as det_writer  # noqa: E402
from editor_manifest import writer as save_writer  # noqa: E402
from setup.template import render_template  # noqa: E402
from web_editor.models import WebEditorError, load_run  # noqa: E402
from web_editor.server import make_server  # noqa: E402


def _make_pdf(path: Path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    pg.insert_textbox(fitz.Rect(48, 18, 564, 40), "Running Header", fontsize=9, align=1)
    doc.save(str(path)); doc.close()


def _make_run(tmp: Path) -> Path:
    _make_pdf(tmp / "in.pdf")
    det = detect_pdf(tmp / "in.pdf")
    man = det_writer.build_manifest([det_writer.case("t", str(tmp / "in.pdf"), det["pages"])],
                                    name="picker_cmc", mode="detector")
    det_writer.write_manifest(tmp / "detected_manifest.json", man)
    save_writer.write_manifest(tmp / "editor_save_manifest.json",
                               save_writer.build_initial(man, source_pdf=str(tmp / "in.pdf"),
                                                         source_detector_manifest=str(tmp / "detected_manifest.json")))
    return tmp


@contextmanager
def _server(run_dir: Path):
    srv = make_server(load_run(run_dir), "127.0.0.1", 0)
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        yield (base, lambda p: urllib.request.urlopen(base + p).read())
    finally:
        srv.shutdown(); srv.server_close()


# (1) server starts with an existing run-dir
def test_server_starts_with_run_dir(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        assert json.loads(get("/api/health"))["ok"]


# (2) server starts from a setup YAML and creates run artifacts
def test_setup_mode_creates_artifacts(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("rwe", PKG / "tools" / "run_web_editor.py")
    rwe = importlib.util.module_from_spec(spec); spec.loader.exec_module(rwe)
    _make_pdf(tmp_path / "in.pdf")
    cfg = yaml.safe_load(render_template())
    cfg["project"]["name"] = "t"; cfg["input"]["pdf_path"] = str(tmp_path / "in.pdf")
    cfg["output"]["artifact_dir"] = str(tmp_path / "out")
    cfg["output"]["save_manifest_path"] = str(tmp_path / "out" / "save.json")
    (tmp_path / "setup.yaml").write_text(yaml.safe_dump(cfg))
    run_dir = rwe._run_dir_from_setup(str(tmp_path / "setup.yaml"))
    assert (Path(run_dir) / "detected_manifest.json").exists()
    assert (tmp_path / "out" / "save.json").exists()


# (3)(4) health + run
def test_run_metadata(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        run = json.loads(get("/api/run"))
        assert run["ok"] and run["schema_version"] == "web-editor-run-v0"
        assert run["page_count"] == 1 and run["source_pdf"].endswith("in.pdf")
        assert run["coordinate_unit"] == "pdf_pt" and run["coordinate_origin"] == "top-left"


# (5) page PNG
def test_page_png(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        png = get("/api/page/1/png?scale=1.5")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"


# (6) page objects
def test_page_objects(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        po = json.loads(get("/api/page/1/objects"))
        assert po["page"] == 1 and len(po["figures"]) >= 1
        assert all(k in po for k in ("figures", "tables", "common_regions"))
        assert po["figures"][0]["object_id"].startswith("figure:")


# (7) object lookup
def test_object_lookup(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        oid = json.loads(get("/api/page/1/objects"))["figures"][0]["object_id"]
        obj = json.loads(get("/api/object/" + oid))
        assert obj["object_id"] == oid and obj["kind"] == "figure" and obj["object"]["body_region"]


# (8) static assets served
def test_static_assets(tmp_path):
    with _server(_make_run(tmp_path)) as (_, get):
        assert b"picker_cmc viewer" in get("/")
        assert b"drawOverlays" in get("/static/app.js")
        assert b"#toolbar" in get("/static/styles.css")


# (9) invalid run-dir -> structured error
def test_invalid_run_dir(tmp_path):
    with pytest.raises(WebEditorError) as e:
        load_run(tmp_path / "does_not_exist")
    assert e.value.code == "RUN_DIR_NOT_FOUND"


# (10) invalid editor-save-manifest is rejected BEFORE the server starts
def test_invalid_manifest_rejected(tmp_path):
    _make_run(tmp_path)
    bad = json.loads((tmp_path / "editor_save_manifest.json").read_text())
    bad["coordinate_origin"] = "bottom-left"
    (tmp_path / "editor_save_manifest.json").write_text(json.dumps(bad))
    with pytest.raises(WebEditorError) as e:
        load_run(tmp_path)
    assert e.value.code == "RUN_MANIFEST_INVALID"
