"""D26 setup-YAML web workflow + run launcher tests (synthetic PDF)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
FROZEN = PKG / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402
from setup.template import render_template  # noqa: E402
from web_editor.models import Workspace, load_run  # noqa: E402
from web_editor.server import make_server  # noqa: E402


@contextmanager
def _workspace_server(tmp: Path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    doc.save(str(tmp / "in.pdf")); doc.close()
    ws = Workspace(runs_root=tmp / "runs")
    srv = make_server(ws, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(p):
        return urllib.request.urlopen(base + p).read()

    def post(p, d):
        req = urllib.request.Request(base + p, data=json.dumps(d).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())
    try:
        yield tmp, get, post
    finally:
        srv.shutdown(); srv.server_close()


def _valid_setup_yaml(tmp: Path) -> str:
    cfg = yaml.safe_load(render_template())
    cfg["project"]["name"] = "run1"
    cfg["input"]["pdf_path"] = str(tmp / "in.pdf")
    cfg["output"]["artifact_dir"] = str(tmp / "runs" / "run1")
    cfg["output"]["save_manifest_path"] = str(tmp / "runs" / "run1" / "editor_save_manifest.json")
    return yaml.safe_dump(cfg)


# (1) template returns commented YAML text
def test_template_endpoint(tmp_path):
    with _workspace_server(tmp_path) as (_, get, _post):
        t = get("/api/setup/template").decode()
        assert t.lstrip().startswith("#") and "schema_version: setup-yaml-v0" in t and "CHANGE_ME" in t


# (2) valid setup validates ok
def test_validate_ok(tmp_path):
    with _workspace_server(tmp_path) as (tmp, _get, post):
        assert post("/api/setup/validate", {"setup_yaml": _valid_setup_yaml(tmp)})["ok"] is True


# (3) invalid setup -> structured setup error
def test_validate_invalid(tmp_path):
    with _workspace_server(tmp_path) as (tmp, _get, post):
        cfg = yaml.safe_load(_valid_setup_yaml(tmp)); del cfg["input"]["pdf_path"]
        r = post("/api/setup/validate", {"setup_yaml": yaml.safe_dump(cfg)})
        assert r["error_code"] == "SETUP_MISSING_FIELD" and r["field"] == "input.pdf_path"


# (4) placeholder -> SETUP_PLACEHOLDER_UNRESOLVED
def test_validate_placeholder(tmp_path):
    with _workspace_server(tmp_path) as (_, _get, post):
        r = post("/api/setup/validate", {"setup_yaml": render_template()})
        assert r["error_code"] == "SETUP_PLACEHOLDER_UNRESOLVED"


# (5) setup run creates detected + editor manifests
def test_setup_run_creates_manifests(tmp_path):
    with _workspace_server(tmp_path) as (tmp, _get, post):
        r = post("/api/setup/run", {"setup_yaml": _valid_setup_yaml(tmp)})
        assert r["ok"] and r["run_id"] == "run1" and r["page_count"] == 1
        assert (tmp / "runs" / "run1" / "detected_manifest.json").exists()
        assert (tmp / "runs" / "run1" / "editor_save_manifest.json").exists()


# (6) created run opens in the viewer APIs
def test_created_run_opens(tmp_path):
    with _workspace_server(tmp_path) as (tmp, get, post):
        post("/api/setup/run", {"setup_yaml": _valid_setup_yaml(tmp)})
        assert json.loads(get("/api/health"))["has_run"] is True
        assert json.loads(get("/api/pages"))["pages"] == [1]
        assert json.loads(get("/api/page/1/objects"))["figures"]
        runs = json.loads(get("/api/runs"))["runs"]
        assert any(x["run_id"] == "run1" for x in runs)
        assert json.loads(get("/api/run/run1"))["run_id"] == "run1"


# (7) before any run, viewer endpoints report NO_RUN_OPEN (not a crash)
def test_no_run_open_guard(tmp_path):
    with _workspace_server(tmp_path) as (_, get, _post):
        assert json.loads(get("/api/health"))["has_run"] is False
        try:
            get("/api/pages")
            assert False
        except urllib.error.HTTPError as e:
            assert json.loads(e.read())["error_code"] == "NO_RUN_OPEN"


# (8) existing run-dir mode still works (backward compat)
def test_run_dir_mode_backcompat(tmp_path):
    # build a run via setup, then serve it directly as a RunContext (D23 style)
    with _workspace_server(tmp_path) as (tmp, _get, post):
        post("/api/setup/run", {"setup_yaml": _valid_setup_yaml(tmp)})
    ctx = load_run(tmp_path / "runs" / "run1")
    srv = make_server(ctx, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert json.loads(urllib.request.urlopen(base + "/api/run").read())["page_count"] == 1
    finally:
        srv.shutdown(); srv.server_close()


# (9) RTM regression unchanged (detector untouched by D26)
def test_rtm_frozen_body_unchanged(tmp_path):
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4))
