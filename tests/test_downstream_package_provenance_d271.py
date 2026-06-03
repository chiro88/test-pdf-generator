"""D27.1 downstream package provenance: source_editor_manifest must be the editor
manifest (not detector-output)."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
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
    doc.save(str(tmp / "in.pdf")); doc.close()
    det = detect_pdf(tmp / "in.pdf")
    man = det_writer.build_manifest([det_writer.case("t", str(tmp / "in.pdf"), det["pages"])],
                                    name="picker_cmc", mode="detector")
    det_writer.write_manifest(tmp / "detected_manifest.json", man)
    save_writer.write_manifest(tmp / "editor_save_manifest.json",
                               save_writer.build_initial(man, source_pdf=str(tmp / "in.pdf"),
                                                         source_detector_manifest=str(tmp / "detected_manifest.json")))
    ctx = load_run(tmp)
    edit_bbox(ctx, f"figure:{ctx.manifest['pages'][0]['figures'][0]['index']}:page1", "body_region", EDIT)
    save(ctx)
    return ctx


# (1) CLI --manifest -> source_editor_manifest points to that editor manifest, NOT detector
def test_cli_records_editor_manifest(tmp_path):
    _run(tmp_path)
    em = tmp_path / "editor_save_manifest.json"
    cli = PKG / "tools" / "export_downstream_package.py"
    proc = subprocess.run([sys.executable, str(cli), "--manifest", str(em),
                           "--out", str(tmp_path / "pkg"), "--json"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    assert pkg["source_editor_manifest"] == str(em)
    assert pkg["source_editor_manifest"].rsplit("/", 1)[-1] != "detected_manifest.json"


# (2) validator rejects a source_editor_manifest pointing at detected_manifest.json
def test_validator_rejects_detector_provenance(tmp_path):
    _run(tmp_path)
    pkg = json.loads((tmp_path / "pkg.json").write_text("{}") or "{}") if False else {}
    # build a valid-looking package then poison provenance
    ctx = load_run(tmp_path)
    build_package(ctx.manifest, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    assert validate_package(pkg) == []
    pkg["source_editor_manifest"] = str(tmp_path / "detected_manifest.json")
    errs = validate_package(pkg)
    assert any("source_editor_manifest" in e and "detected_manifest" in e for e in errs)


# (3) objects/crops still use the edited bbox
def test_objects_use_edited_bbox(tmp_path):
    ctx = _run(tmp_path)
    build_package(ctx.manifest, tmp_path / "pkg", source_manifest_path=str(tmp_path / "editor_save_manifest.json"))
    pkg = json.loads((tmp_path / "pkg" / "package_manifest.json").read_text())
    fig = next(o for o in pkg["objects"] if o["kind"] == "figure")
    assert fig["body_region"] == EDIT and (tmp_path / "pkg" / fig["crops"]["body"]).exists()


# (4) web export API also writes the correct (editor) source_editor_manifest
def test_web_export_records_editor_manifest(tmp_path):
    ctx = _run(tmp_path)
    ws = Workspace(runs_root=tmp_path.parent); ws.register(ctx)
    srv = make_server(ws, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/api/export/downstream", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req).read())
        assert r["ok"]
        pkg = json.loads((tmp_path / "downstream_package" / "package_manifest.json").read_text())
        assert pkg["source_editor_manifest"].rsplit("/", 1)[-1] == "editor_save_manifest.json"
        assert validate_package(pkg) == []
    finally:
        srv.shutdown(); srv.server_close()


# (5) exporting a detector-output manifest (wrong input) is rejected
def test_reject_detector_output_input(tmp_path):
    _run(tmp_path)
    det = json.loads((tmp_path / "detected_manifest.json").read_text())
    with pytest.raises(ExportError):
        build_package(det, tmp_path / "pkg", source_manifest_path=str(tmp_path / "detected_manifest.json"))
