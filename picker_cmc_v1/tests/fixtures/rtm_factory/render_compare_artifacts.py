#!/usr/bin/env python3
"""CLI: render D4 compare results into review overlays (D5).

    python render_compare_artifacts.py \
        --truth-root picker_cmc_v1/tests/fixtures/rtm_frozen \
        --detected detected_manifest.json \
        --compare-report artifacts/rtm_compare/compare_report.json \
        --out artifacts/rtm_overlay

Truth source principle:
    rtm_gallery = generated candidates / development only
    rtm_frozen  = human-reviewed golden source

This visualizes D4 output; it does not run a detector. Exit 2 on invalid input.
"""
from __future__ import annotations

import argparse
import sys

from rtm_factory.compare import InvalidInput
from rtm_factory.overlay import OverlayConfig, generate


def main() -> None:
    ap = argparse.ArgumentParser(description="Render truth/detected overlay artifacts from a D4 compare report.")
    ap.add_argument("--truth-root", required=True, help="rtm_frozen (golden) or rtm_gallery (dev) dir")
    ap.add_argument("--detected", required=True, help="detector output manifest JSON")
    ap.add_argument("--compare-report", required=True, help="D4 compare_report.json")
    ap.add_argument("--out", default="artifacts/rtm_overlay", help="overlay output dir")
    ap.add_argument("--case-id", default=None, help="restrict to one case_id")
    ap.add_argument("--failures-only", action="store_true", help="only render pages with comparison failures")
    ap.add_argument("--all", dest="all_cases", action="store_true", help="render all cases/pages even if all-pass")
    ap.add_argument("--pages", default=None, help="comma-separated page numbers to restrict to")
    ap.add_argument("--scale", type=float, default=1.5, help="render scale (PNG px = pt * scale)")
    args = ap.parse_args()

    if args.truth_root.rstrip("/").endswith("rtm_gallery"):
        print("note: overlaying against rtm_gallery (generated candidates) — development only.", file=sys.stderr)

    pages = [int(x) for x in args.pages.split(",") if x.strip()] if args.pages else None
    config = OverlayConfig(scale=args.scale, failures_only=args.failures_only, all_cases=args.all_cases,
                           case_id_filter=args.case_id, pages_filter=pages)

    try:
        result = generate(args.truth_root, args.detected, args.compare_report, args.out, config)
    except InvalidInput as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"overlay: {result['pages_rendered']} page(s) rendered across {len(result['cases'])} case(s)")
    print(f"outputs: {result['manifest']} | {result['index']}")


if __name__ == "__main__":
    main()
