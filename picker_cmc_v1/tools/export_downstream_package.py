#!/usr/bin/env python3
"""D27: export a downstream-package-v0 from an editor-save-manifest-v0.

    python tools/export_downstream_package.py \
        --manifest artifacts/picker_run/editor_save_manifest.json \
        --out artifacts/picker_run/downstream_package --json

Per-object caption/body/context crops + metadata JSON + JSONL + index, from the
human-edited bboxes. No content interpretation, no LLM calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from editor_manifest.validator import validate_manifest  # noqa: E402
from downstream_package.exporter import ExportError, build_package  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export a downstream-package-v0 (D27).")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error_code": "MANIFEST_UNREADABLE", "error": str(exc)}
        print(json.dumps(payload) if args.json else f"ERROR {exc}", file=(sys.stdout if args.json else sys.stderr))
        return 2
    errors = validate_manifest(manifest)
    if errors:
        payload = {"ok": False, "error_code": "MANIFEST_INVALID", "errors": errors}
        print(json.dumps(payload) if args.json else "INVALID: " + "; ".join(errors),
              file=(sys.stdout if args.json else sys.stderr))
        return 2

    try:
        summary = build_package(manifest, args.out, source_manifest_path=args.manifest)
    except ExportError as exc:
        payload = {"ok": False, "error_code": "EXPORT_FAILED", "error": str(exc)}
        print(json.dumps(payload) if args.json else f"ERROR {exc}", file=(sys.stdout if args.json else sys.stderr))
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"OK: {summary['objects']} objects ({summary['figures']} fig / {summary['tables']} tbl), "
              f"{summary['crops']} crops -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
