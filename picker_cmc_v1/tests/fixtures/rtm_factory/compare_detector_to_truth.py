#!/usr/bin/env python3
"""CLI: compare a detector output manifest against RTM truth (D4).

    python compare_detector_to_truth.py \
        --truth-root picker_cmc_v1/tests/fixtures/rtm_frozen \
        --detected detected_manifest.json \
        --out artifacts/rtm_compare

Truth source principle:
    rtm_gallery = generated candidates / development comparison only
    rtm_frozen  = human-reviewed golden comparison source

Exit codes: 0 pass · 1 comparison failed · 2 invalid input/schema.
comparison pass != detector correctness on real documents.
"""
from __future__ import annotations

import argparse
import sys

from rtm_factory.compare import (
    ComparisonConfig,
    InvalidInput,
    ToleranceProfile,
    compare_cases,
    load_detected_manifest,
    load_truth_cases,
    write_compare_report,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare detector output manifest vs RTM truth (golden comparison).")
    ap.add_argument("--truth-root", required=True, help="rtm_frozen (golden) or rtm_gallery (dev) dir")
    ap.add_argument("--detected", required=True, help="detector output manifest JSON")
    ap.add_argument("--out", default="artifacts/rtm_compare", help="artifacts output dir")
    ap.add_argument("--tolerance-profile", default="strict", choices=["strict", "loose"])
    ap.add_argument("--allow-extra", action="store_true", help="do not fail on extra detected objects")
    ap.add_argument("--case-id", default=None, help="restrict comparison to one case_id")
    ap.add_argument("--region-kind", default=None, choices=["figure", "table", "header", "footer", "watermark"])
    args = ap.parse_args()

    if args.truth_root.rstrip("/").endswith("rtm_gallery"):
        print("note: comparing against rtm_gallery (generated candidates) — development only, not a golden gate.",
              file=sys.stderr)

    try:
        config = ComparisonConfig(
            tolerance=ToleranceProfile.named(args.tolerance_profile),
            allow_extra=args.allow_extra,
            case_id_filter=args.case_id,
            region_kind_filter=args.region_kind,
        )
        truth_cases = load_truth_cases(args.truth_root, case_filter=args.case_id)
        detected = load_detected_manifest(args.detected)
        report = compare_cases(truth_cases, detected, config)
    except InvalidInput as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        sys.exit(2)

    json_path, md_path = write_compare_report(report, args.out)
    s = report["summary"]
    print(f"compare: {s['cases_passed']}/{s['cases_total']} cases passed, "
          f"{s['regions_failed']} region failures, {s['objects_missing']} missing, {s['objects_extra']} extra")
    print(f"reports: {json_path} | {md_path}")
    sys.exit(0 if s["cases_failed"] == 0 else 1)


if __name__ == "__main__":
    main()
