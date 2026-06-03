"""D24 web editor bbox edit / save / save-as / ruler tests (synthetic PDF, API level)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402
from detector_output import writer as det_writer  # noqa: E402
from editor_manifest import writer as save_writer  # noqa: E402
from editor_manifest.validator import validate_manifest  # noqa: E402
from web_editor.coords import ruler_measure, screen_to_pdf_pt  # noqa: E402
from web_editor.models import load_run  # noqa: E402
from web_editor.server import make_server  # noqa: E402


def _make_run(tmp: Path) -> Path:
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    doc.save(str(tmp / "in.pdf")); doc.close()
    det = detect_pdf(tmp / "in.pdf")
    man = det_writer.build_manifest([det_writer.case("t", str(tmp / "in.pdf"), det["pages"])],
                                    name="picker_cmc", mode="detector")
    det_writer.write_manifest(tmp / "detected_manifest.json", man)
    save_writer.write_manifest(tmp / "editor_save_manifest.json",
                               save_writer.build_initial(man, source_pdf=str(tmp / "in.pdf"),
                                                         source_detector_manifest=str(tmp / "detected_manifest.json")))
    return tmp


@contextmanager
def _server(tmp: Path):
    srv = make_server(load_run(_make_run(tmp)), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(p):
        return json.loads(urllib.request.urlopen(base + p).read())

    def post(p, body):
        req = urllib.request.Request(base + p, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())
    try:
        yield get, post, base
    finally:
        srv.shutdown(); srv.server_close()


def _fig_id(get):
    return get("/api/page/1/objects")["figures"][0]["object_id"]


# (1)(2) edit updates bbox in memory + edit log appended with before/after
def test_edit_updates_and_logs(tmp_path):
    with _server(tmp_path) as (get, post, _):
        oid = _fig_id(get)
        res = post("/api/edit/bbox", {"object_id": oid, "region": "body_region", "bbox": [110, 110, 490, 210]})
        assert res["ok"] and res["after"] == [110, 110, 490, 210] and res["dirty"]
        man = get("/api/manifest")
        edit = man["edits"][-1]
        assert edit["operation"] == "update_bbox" and edit["after"] == [110, 110, 490, 210] and edit["before"]


# (3) invalid object_id rejected
def test_invalid_object(tmp_path):
    with _server(tmp_path) as (get, post, _):
        r = post("/api/edit/bbox", {"object_id": "figure:99:page1", "region": "body_region", "bbox": [1, 1, 2, 2]})
        assert r["error_code"] == "EDIT_OBJECT_NOT_FOUND"


# (4) invalid region rejected
def test_invalid_region(tmp_path):
    with _server(tmp_path) as (get, post, _):
        r = post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "nope", "bbox": [1, 1, 2, 2]})
        assert r["error_code"] == "EDIT_REGION_NOT_FOUND"


# (5) bbox outside page rejected
def test_out_of_bounds(tmp_path):
    with _server(tmp_path) as (get, post, _):
        r = post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [1, 1, 9999, 9999]})
        assert r["error_code"] == "EDIT_OUT_OF_PAGE_BOUNDS"
        r2 = post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [400, 400, 100, 100]})
        assert r2["error_code"] == "EDIT_BAD_BBOX"   # x0<x1 / y0<y1 violated


# (6) save writes a valid editor-save-manifest-v0
def test_save_writes_valid(tmp_path):
    with _server(tmp_path) as (get, post, _):
        post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [110, 110, 490, 210]})
        r = post("/api/save", {})
        assert r["ok"] and r["dirty"] is False
        saved = json.loads((tmp_path / "editor_save_manifest.json").read_text())
        assert validate_manifest(saved) == [] and saved["edits"]


# (7)(8) save-as writes a separate file under the run dir; traversal rejected
def test_save_as(tmp_path):
    with _server(tmp_path) as (get, post, _):
        post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [110, 110, 490, 210]})
        r = post("/api/save-as", {"path": "versions/v1.json"})
        assert r["ok"] and (tmp_path / "versions" / "v1.json").exists()
        bad = post("/api/save-as", {"path": "../escape.json"})
        assert bad["error_code"] == "SAVE_PATH_NOT_ALLOWED"
        assert not (tmp_path.parent / "escape.json").exists()


# (9) edited overlay API reflects the new bbox
def test_overlay_reflects_edit(tmp_path):
    with _server(tmp_path) as (get, post, _):
        oid = _fig_id(get)
        post("/api/edit/bbox", {"object_id": oid, "region": "body_region", "bbox": [111, 112, 491, 211]})
        ov = get("/api/page/1/overlays")["overlays"]
        body = next(o for o in ov if o["object_id"] == oid and o["region"] == "body_region")
        assert body["bbox"] == [111, 112, 491, 211]


# (10) page PNG still returns PNG after edits
def test_png_still_works(tmp_path):
    with _server(tmp_path) as (get, post, base):
        post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [110, 110, 490, 210]})
        png = urllib.request.urlopen(base + "/api/page/1/png").read()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"


# (11) ruler coordinate conversion + measurement helpers
def test_ruler_helpers():
    assert screen_to_pdf_pt(150, 1.5) == 100.0
    m = ruler_measure([10, 10], [40, 50])
    assert m["dx"] == 30 and m["dy"] == 40 and m["distance"] == 50.0


# (12) static UI still served (with the D24 controls)
def test_static_ui(tmp_path):
    with _server(tmp_path) as (get, post, base):
        html = urllib.request.urlopen(base + "/").read()
        js = urllib.request.urlopen(base + "/static/app.js").read()
        assert b"mode-edit" in html and b"save-as" in html and b"/api/edit/bbox" in js


# edit-state endpoint reflects dirty + edit count
def test_edit_state(tmp_path):
    with _server(tmp_path) as (get, post, _):
        assert get("/api/edit-state")["dirty"] is False
        post("/api/edit/bbox", {"object_id": _fig_id(get), "region": "body_region", "bbox": [110, 110, 490, 210]})
        st = get("/api/edit-state")
        assert st["dirty"] is True and st["edit_count"] == 1
