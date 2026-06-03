#!/usr/bin/env python3
"""D25: export post-edit overlays/crops from an editor-save-manifest-v0.

    python tools/export_editor_manifest_artifacts.py \
        --manifest artifacts/picker_run/versions/edited.json \
        --out artifacts/picker_run/edited_review --json

The SAVED (edited) manifest is the source of truth — overlays/crops reflect the
latest edited bboxes, not a fresh detector run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from editor_manifest.validator import validate_manifest  # noqa: E402
from web_editor.export import ExportError, export_artifacts  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export post-edit artifacts from an editor-save-manifest (D25).")
    ap.add_argument("--manifest", required=True, help="editor-save-manifest-v0 (the edited manifest)")
    ap.add_argument("--out", required=True, help="output dir for overlays/crops + index/summary")
    ap.add_argument("--json", action="store_true", help="emit the export summary as pure JSON")
    args = ap.parse_args(argv)

    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error_code": "MANIFEST_UNREADABLE", "error": str(exc)}
        print(json.dumps(payload) if args.json else f"ERROR {exc}", file=sys.stderr if not args.json else sys.stdout)
        return 2
    errors = validate_manifest(manifest)
    if errors:
        payload = {"ok": False, "error_code": "MANIFEST_INVALID", "errors": errors}
        print(json.dumps(payload) if args.json else "INVALID: " + "; ".join(errors),
              file=sys.stderr if not args.json else sys.stdout)
        return 2

    try:
        summary = export_artifacts(manifest, args.out)
    except ExportError as exc:
        payload = {"ok": False, "error_code": "EXPORT_FAILED", "error": str(exc)}
        print(json.dumps(payload) if args.json else f"ERROR {exc}", file=sys.stderr if not args.json else sys.stdout)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"OK: {summary['figures']} figures / {summary['tables']} tables, "
              f"{summary['edit_count']} edit(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
