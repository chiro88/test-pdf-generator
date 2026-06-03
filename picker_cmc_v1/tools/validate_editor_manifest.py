#!/usr/bin/env python3
"""D22: validate an editor-save-manifest-v0 file.

    python tools/validate_editor_manifest.py --manifest editor_save_manifest.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from editor_manifest.validator import validate_manifest  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate an editor-save-manifest-v0 (D22).")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error_code": "MANIFEST_UNREADABLE", "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"ERROR {exc}",
              file=(sys.stdout if args.json else sys.stderr))
        return 2

    errors = validate_manifest(data)
    payload = {"ok": not errors, "errors": errors}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("VALID" if not errors else "INVALID:\n  " + "\n  ".join(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
