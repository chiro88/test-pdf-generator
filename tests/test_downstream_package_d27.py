"""D27 downstream-package-v0 export tests (synthetic PDF)."""
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
from downstream_package.exporter import ExportError, build_package  # noqa: E402
from downstream_package.validator import validate_package  # noqa: E402
from web_editor.editing import edit_bbox, save  # noqa: E402
from web_editor.models import Workspace, load_run  # noqa: E402
from web_editor.server import make_server  # noqa: E402

EDIT = [110, 108, 490, 210]


def _run(tmp: Path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 Example waveform", fontsize=10)
    pg.insert_text((100, 300), "Table 1 Measurements", fontsize=10)
    for i in range(4):
        pg.insert_text((100, 320 + i * 16), f"Row {i} value {i}", fontsize=9)
    doc.save(str(tmp / "in.pdf")); doc.close()
    det = detect_pdf(tmp / "in.pdf")
    man = det_writer.build_manifest([det_writer.case("t", str(tmp / "in.pdf"), det["pages"])],
                                    name="picker_cmc", mode="detector")
    det_writer.write_manifest(tmp / "detected_manifest.json", man)
    save_writer.write_manifest(tmp / "editor_save_manifest.json",
                               save_writer.build_initial(man, source_pdf=str(tmp / "in.pdf"),
                                                         source_detector_manifest=str(tmp / "detected_manifest.json")))
    ctx = load_run(tmp)
    oid = f"figure:{ctx.manifest['pages'][0]['figures'][0]['index']}:page1"
    edit_bbox(ctx, oid, "body_region", EDIT)
    save(ctx)
    return ctx, oid


# (1)(2)(3) package + validator + jsonl
def test_build_package(tmp_path):
    ctx, _ = _run(tmp_path)
    summary = build_package(ctx.manifest, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))
    assert summary["ok"] and summary["objects"] >= 2
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    assert validate_package(pkg) == []
    jsonl = (tmp_path / "pkg" / "objects.jsonl").read_text().strip().splitlines()
    assert len(jsonl) == len(pkg["objects"]) and all(json.loads(l)["object_id"] for l in jsonl)
    assert (tmp_path / "pkg" / "index.md").exists()


# (4)(5) figure + table caption/body/context crops
def test_crops_per_region(tmp_path):
    ctx, _ = _run(tmp_path)
    build_package(ctx.manifest, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    fig = next(o for o in pkg["objects"] if o["kind"] == "figure")
    tbl = next(o for o in pkg["objects"] if o["kind"] == "table")
    for o in (fig, tbl):
        assert {"caption", "body", "context"} <= set(o["crops"].keys())
        for rel in o["crops"].values():
            assert (tmp_path / "pkg" / rel).exists()
    assert fig["downstream_task_hint"] == "diagram_or_waveform" and tbl["downstream_task_hint"] == "table"


# (6) crop bbox uses the EDITED bbox
def test_crop_uses_edited_bbox(tmp_path):
    ctx, _ = _run(tmp_path)
    build_package(ctx.manifest, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    fig = next(o for o in pkg["objects"] if o["kind"] == "figure")
    assert fig["body_region"] == EDIT


# (7) invalid manifest -> export rejects (no source_pdf)
def test_invalid_manifest_rejected(tmp_path):
    bad = {"schema_version": "editor-save-manifest-v0", "source_pdf": "/nope.pdf",
           "coordinate_unit": "pdf_pt", "coordinate_origin": "top-left", "pages": [], "edits": []}
    with pytest.raises(ExportError):
        build_package(bad, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))


# (8) CLI --json is pure JSON
def test_cli_json(tmp_path):
    import subprocess
    ctx, _ = _run(tmp_path)
    cli = PKG / "tools" / "export_downstream_package.py"
    proc = subprocess.run([sys.executable, str(cli), "--manifest", str(tmp_path / "editor_save_manifest.json"),
                           "--out", str(tmp_path / "pkg"), "--json"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["ok"] and out["objects"] >= 2


# (9) web export API builds the package under the run dir
def test_web_export_api(tmp_path):
    ctx, _ = _run(tmp_path)
    ws = Workspace(runs_root=tmp_path.parent); ws.register(ctx)
    srv = make_server(ws, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/api/export/downstream", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req).read())
        assert r["ok"] and r["objects"] >= 2
        assert (tmp_path / "downstream_package" / "package_manifest.json").exists()
    finally:
        srv.shutdown(); srv.server_close()


# (10) RTM regression unchanged
def test_rtm_frozen_body_unchanged(tmp_path):
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4))
