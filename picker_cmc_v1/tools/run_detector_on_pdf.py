#!/usr/bin/env python3
"""D17: run the no-truth detector on a real PDF and build an operator review package.

    python tools/run_detector_on_pdf.py --pdf /path/to/input.pdf \
        --out artifacts/real_pdf_smoke/<name> --json

Produces under --out: detected_manifest.json (detector-output-v0), review_index.md,
summary.json, pages/page_NNN_overlay.png, crops/<figure|table>_<index>_body.png.

There is no ground truth for a real PDF, so this makes NO correctness claim — the
output is a visual review package for an operator. The input PDF is read as an
artifact source and is NOT written into the repo.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from detector.review_artifacts import ReviewInputError, build_review_package  # noqa: E402


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload.get("ok"):
            print(f"OK: {payload['pdf']} -> {payload['pages']} pages, "
                  f"{payload['figures_detected']} figures, {payload['tables_detected']} tables")
            print(f"  manifest:     {payload['artifacts']['manifest']}")
            print(f"  review_index: {payload['artifacts']['review_index']}")
            for w in payload.get("warnings", []):
                print(f"  warning: {w}")
        else:
            print(f"ERROR [{payload.get('error_code')}]: {payload.get('error')}", file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="No-truth detector real-PDF review harness (D17).")
    ap.add_argument("--pdf", required=True, help="input PDF (not committed to the repo)")
    ap.add_argument("--out", required=True, help="output artifact directory")
    ap.add_argument("--name", default=None, help="logical name (defaults to the PDF stem)")
    ap.add_argument("--scale", type=float, default=2.0, help="overlay render scale")
    ap.add_argument("--no-crops", action="store_true", help="skip figure/table body crops")
    ap.add_argument("--json", action="store_true", help="emit pure JSON")
    args = ap.parse_args(argv)

    try:
        summary = build_review_package(args.pdf, args.out, name=args.name, scale=args.scale,
                                       crops=not args.no_crops)
    except ReviewInputError as exc:
        _emit({"ok": False, "error_code": "INVALID_PDF_INPUT", "error": str(exc), "pdf": args.pdf}, args.json)
        return 2
    _emit(summary, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
