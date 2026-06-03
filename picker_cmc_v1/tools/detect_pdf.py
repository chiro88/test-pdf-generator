#!/usr/bin/env python3
"""Run the no-truth detector on one PDF and emit detector-output-v0 pages (D11).

    python tools/detect_pdf.py --pdf <file.pdf> --out <case.json>

Writes {"pages": [...]} — the per-case payload the RTM runner's --detector-cmd
expects. This reads ONLY the PDF (and optional --setup); it never opens truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1 (detector + detector_output)

from detector.pipeline import detect_pdf  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="No-truth detector on one PDF -> detector-output-v0 pages.")
    ap.add_argument("--pdf", required=True, help="input PDF to run the no-truth detector on")
    ap.add_argument("--out", required=True, help="output path for the detector-output-v0 pages JSON")
    ap.add_argument("--setup", default=None, help="optional detector config (unused in baseline)")
    args = ap.parse_args(argv)

    result = detect_pdf(args.pdf)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
