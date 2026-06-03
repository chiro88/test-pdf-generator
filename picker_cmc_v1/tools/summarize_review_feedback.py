#!/usr/bin/env python3
"""D19: summarize a real-PDF operator review into next-task recommendations.

    python tools/summarize_review_feedback.py \
        --review review_result.yaml \
        --detected artifacts/real_pdf_smoke/<name>/detected_manifest.json \
        --out artifacts/real_pdf_smoke/<name>/review_summary.json --json

Reads the operator's review_result (YAML/JSON) + the detector-output manifest,
validates the review against the detected objects, and writes a review_summary
with per-issue counts and recommended next detector tasks. Makes no correctness
claim and tunes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from detector.review_feedback import ReviewError, load_review, summarize  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Summarize a real-PDF operator review (D19).")
    ap.add_argument("--review", required=True, help="review_result.yaml|json")
    ap.add_argument("--detected", default=None, help="detector-output-v0 manifest (enables object_id checks)")
    ap.add_argument("--out", default=None, help="write the summary JSON here")
    ap.add_argument("--json", action="store_true", help="emit pure JSON to stdout")
    args = ap.parse_args(argv)

    try:
        review = load_review(args.review)
        detected = json.loads(Path(args.detected).read_text(encoding="utf-8")) if args.detected else None
        summary = summarize(review, detected)
    except (ReviewError, FileNotFoundError, json.JSONDecodeError) as exc:
        payload = {"ok": False, "error_code": "INVALID_REVIEW", "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"ERROR: {exc}",
              file=(sys.stdout if args.json else sys.stderr))
        return 2

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"reviewed {summary['reviewed_objects']} objects: {summary['accepted']} accepted, "
              f"{summary['missed_objects']} missed")
        for issue, n in summary["issues"].items():
            if n:
                print(f"  {issue}: {n}")
        for t in summary["recommended_next_tasks"]:
            print(f"  -> {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
