"""D25 edit persistence + post-edit artifact export tests (synthetic PDF)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
FROZEN = PKG / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402
from detector_output import writer as det_writer  # noqa: E402
from editor_manifest import writer as save_writer  # noqa: E402
from editor_manifest.validator import validate_manifest  # noqa: E402
from web_editor.export import export_artifacts  # noqa: E402
from web_editor.manifest_view import page_objects  # noqa: E402
from web_editor.models import WebEditorError, load_run  # noqa: E402
from web_editor.server import make_server  # noqa: E402

EDIT = [120, 118, 480, 205]


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


def _edit_and(tmp: Path, *, save=True, save_as=None):
    """Run a server, apply one body_region edit, optionally save/save-as; return object_id."""
    srv = make_server(load_run(_make_run(tmp)), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(p, d):
        req = urllib.request.Request(base + p, data=json.dumps(d).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    oid = json.loads(urllib.request.urlopen(base + "/api/page/1/objects").read())["figures"][0]["object_id"]
    post("/api/edit/bbox", {"object_id": oid, "region": "body_region", "bbox": EDIT})
    if save:
        post("/api/save", {})
    if save_as:
        post("/api/save-as", {"path": save_as})
    srv.shutdown(); srv.server_close()
    return oid


def _body(manifest, oid):
    return next(o for o in page_objects(manifest, 1)["figures"] if o["object_id"] == oid)["body_region"]


# (1) edit -> save -> reload default context -> edited bbox persists
def test_reload_persists_edit(tmp_path):
    oid = _edit_and(tmp_path, save=True)
    ctx = load_run(tmp_path)
    assert _body(ctx.manifest, oid) == EDIT


# (2) edit -> save-as -> open with --manifest -> edited bbox persists
def test_save_as_reopen(tmp_path):
    oid = _edit_and(tmp_path, save=False, save_as="versions/edited.json")
    ctx = load_run(tmp_path, manifest_path=tmp_path / "versions" / "edited.json")
    assert ctx.manifest["pages"][0]["figures"][0]["body_region"] == EDIT


# (3) edit log preserved after reload
def test_edit_log_preserved(tmp_path):
    _edit_and(tmp_path, save=True)
    ctx = load_run(tmp_path)
    assert ctx.manifest["edits"] and ctx.manifest["edits"][-1]["after"] == EDIT


# (4) overlay API reflects the reloaded edited bbox
def test_overlay_after_reload(tmp_path):
    oid = _edit_and(tmp_path, save=True)
    srv = make_server(load_run(tmp_path), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        ov = json.loads(urllib.request.urlopen(base + "/api/page/1/overlays").read())["overlays"]
        body = next(o for o in ov if o["object_id"] == oid and o["region"] == "body_region")
        assert body["bbox"] == EDIT
    finally:
        srv.shutdown(); srv.server_close()


# (5)(6) export builds index/summary/overlay/crop using the EDITED bbox
def test_export_uses_edited_bbox(tmp_path):
    _edit_and(tmp_path, save=True)
    ctx = load_run(tmp_path)
    summary = export_artifacts(ctx.manifest, tmp_path / "edited_review")
    assert (tmp_path / "edited_review" / "index.md").exists()
    assert (tmp_path / "edited_review" / "summary.json").exists()
    assert summary["artifacts"]["pages"] and summary["artifacts"]["crops"]
    fig = next(o for o in summary["objects"] if o["kind"] == "figure")
    assert fig["body_region"] == EDIT                       # crop uses edited bbox
    assert (tmp_path / "edited_review" / fig["crop"]).exists()


# (7) invalid explicit manifest rejected
def test_invalid_explicit_manifest(tmp_path):
    _make_run(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "editor-save-manifest-v0",
                               "coordinate_origin": "bottom-left"}))   # invalid
    with pytest.raises(WebEditorError) as e:
        load_run(tmp_path, manifest_path=bad)
    assert e.value.code == "RUN_MANIFEST_INVALID"


# (8) explicit manifest outside the run-dir is rejected (policy)
def test_manifest_outside_run_dir(tmp_path):
    _make_run(tmp_path)
    with pytest.raises(WebEditorError) as e:
        load_run(tmp_path, manifest_path="/etc/hostname")
    assert e.value.code == "MANIFEST_OUTSIDE_RUN_DIR"


# (9) page PNG still works on a reloaded run
def test_png_after_reload(tmp_path):
    _edit_and(tmp_path, save=True)
    srv = make_server(load_run(tmp_path), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        png = urllib.request.urlopen(base + "/api/page/1/png").read()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        srv.shutdown(); srv.server_close()


# (10) RTM regression unchanged (detector untouched by D25)
def test_rtm_frozen_body_unchanged(tmp_path):
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4))
