#!/usr/bin/env python3
"""D23: launch the read-only web editor.

    python tools/run_web_editor.py --run-dir artifacts/picker_run --host 127.0.0.1 --port 8765
    python tools/run_web_editor.py --setup setup.yaml --host 127.0.0.1 --port 8765

--setup mode reuses the D22 flow (detect + write detected_manifest.json +
editor_save_manifest.json under the setup's artifact_dir) and then serves it.
Read-only: no bbox editing, no save, no ruler.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from detector.pipeline import detect_pdf  # noqa: E402
from detector_output import writer as det_writer  # noqa: E402
from editor_manifest import writer as save_writer  # noqa: E402
from setup.errors import SetupError  # noqa: E402
from setup.loader import load_setup  # noqa: E402
from setup.validator import validate_setup  # noqa: E402
from web_editor.models import WebEditorError, Workspace, load_run  # noqa: E402
from web_editor.server import serve  # noqa: E402


def _run_dir_from_setup(setup_path: str) -> Path:
    cfg = validate_setup(load_setup(setup_path))
    pdf_path = cfg["input"]["pdf_path"]
    if not Path(pdf_path).exists():
        raise SetupError("SETUP_INVALID_VALUE", f"input.pdf_path not found: {pdf_path}", field="input.pdf_path")
    out_dir = Path(cfg["output"]["artifact_dir"])
    name = cfg["project"]["name"]
    detection = detect_pdf(pdf_path)
    manifest = det_writer.build_manifest([det_writer.case(name, str(pdf_path), detection["pages"])],
                                         name="picker_cmc", mode="detector")
    det_path = det_writer.write_manifest(out_dir / "detected_manifest.json", manifest)
    save_path = Path(cfg["output"].get("save_manifest_path") or (out_dir / "editor_save_manifest.json"))
    save = save_writer.build_initial(manifest, source_pdf=str(pdf_path), source_detector_manifest=str(det_path))
    save_writer.write_manifest(save_path, save)
    return out_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only picker_cmc web editor (D23).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run-dir", help="existing run directory")
    src.add_argument("--setup", help="setup YAML (creates the run, then serves)")
    ap.add_argument("--manifest", default=None,
                    help="explicit editor-save-manifest-v0 to open (must be inside the run dir)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)

    try:
        run_dir = _run_dir_from_setup(args.setup) if args.setup else args.run_dir
        ctx = load_run(run_dir, manifest_path=args.manifest)
    except (SetupError, WebEditorError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    # D26: a workspace rooted at the run's parent so the setup panel can launch /
    # list sibling runs; the opened run is the current one.
    ws = Workspace(runs_root=ctx.run_dir.parent)
    ws.register(ctx)
    serve(ws, args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
