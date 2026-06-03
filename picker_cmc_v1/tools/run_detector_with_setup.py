#!/usr/bin/env python3
"""D22: run the detector from a setup-yaml-v0 file.

    python tools/run_detector_with_setup.py --setup setup.yaml --json

Loads + validates the setup, runs the no-truth detector on input.pdf_path, writes a
detector-output-v0 manifest (the editable initial proposal) and an initial
editor-save-manifest-v0 under output.artifact_dir. Makes no correctness claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from detector.pipeline import detect_pdf  # noqa: E402
from detector_output import writer as det_writer  # noqa: E402
from editor_manifest import writer as save_writer  # noqa: E402
from setup.errors import SetupError  # noqa: E402
from setup.loader import load_setup  # noqa: E402
from setup.validator import validate_setup  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the detector from a setup YAML (D22).")
    ap.add_argument("--setup", required=True, help="setup-yaml-v0 file (input PDF + output paths)")
    ap.add_argument("--json", action="store_true", help="emit the run summary as pure JSON")
    args = ap.parse_args(argv)

    try:
        cfg = validate_setup(load_setup(args.setup))
    except SetupError as exc:
        payload = exc.to_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"ERROR {exc}",
              file=(sys.stdout if args.json else sys.stderr))
        return 2

    pdf_path = cfg["input"]["pdf_path"]
    if not Path(pdf_path).exists():
        err = {"ok": False, "error_code": "SETUP_INVALID_VALUE", "error": f"input.pdf_path not found: {pdf_path}",
               "field": "input.pdf_path"}
        print(json.dumps(err, ensure_ascii=False, indent=2) if args.json else f"ERROR {err['error']}",
              file=(sys.stdout if args.json else sys.stderr))
        return 2

    out_dir = Path(cfg["output"]["artifact_dir"])
    name = cfg["project"]["name"]

    detection = detect_pdf(pdf_path)  # {"pages": [...]}
    manifest = det_writer.build_manifest([det_writer.case(name, str(pdf_path), detection["pages"])],
                                         name="picker_cmc", mode="detector")
    det_path = det_writer.write_manifest(out_dir / "detected_manifest.json", manifest)

    save_path = Path(cfg["output"].get("save_manifest_path") or (out_dir / "editor_save_manifest.json"))
    save = save_writer.build_initial(manifest, source_pdf=str(pdf_path),
                                     source_detector_manifest=str(det_path))
    save_writer.write_manifest(save_path, save)

    summary = {
        "ok": True,
        "project": name,
        "pdf": str(pdf_path),
        "detector_manifest": str(det_path),
        "editor_save_manifest": str(save_path),
        "pages": len(detection["pages"]),
        "figures": sum(len(p.get("figures", [])) for p in detection["pages"]),
        "tables": sum(len(p.get("tables", [])) for p in detection["pages"]),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"OK: {name}: {summary['figures']} figures / {summary['tables']} tables")
        print(f"  detector_manifest:    {det_path}")
        print(f"  editor_save_manifest: {save_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
