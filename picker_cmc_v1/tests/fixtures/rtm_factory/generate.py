#!/usr/bin/env python3
from __future__ import annotations

import random
import shutil
from pathlib import Path

from rtm_factory.coverage import coverage_summary, derive_tags
from rtm_factory.gallery import write_index, write_manifest
from rtm_factory.render import build_pdf
from rtm_factory.scenario_specs import all_cases
from rtm_factory.self_check import run_self_check

SEED = 1234
ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "rtm_gallery"


def main() -> None:
    rng = random.Random(SEED)
    _ = rng.random()  # Reserve deterministic RNG instance for future scenario expansion.
    cases = all_cases()
    if GALLERY_DIR.exists():
        shutil.rmtree(GALLERY_DIR)
    GALLERY_DIR.mkdir(parents=True)

    entries = []
    for case in cases:
        case_dir = GALLERY_DIR / case.case_id
        truth, png_paths = build_pdf(case, case_dir)
        entries.append(
            {
                "case_id": case.case_id,
                "axes": case.axes,
                "realistic": case.realistic,
                "pdf": f"{case.case_id}/{case.case_id}.pdf",
                "truth": f"{case.case_id}/{case.case_id}.truth.json",
                "preview": f"{case.case_id}/{png_paths[0].name}",
                "page_count": len(truth["pages"]),
                "coverage_tags": derive_tags(case),
            }
        )
    write_manifest(GALLERY_DIR, entries, coverage_summary(cases), seed=SEED)
    write_index(GALLERY_DIR, cases)
    report = run_self_check(GALLERY_DIR)
    ov = report["text_overlap"]
    print(f"generated {len(cases)} RTM candidate cases at {GALLERY_DIR}")
    print(f"text-overlap self-check: {ov['passed']}/{ov['checked']} regions matched, "
          f"{len(ov['skipped'])} skipped (see rtm_gallery/SELF_CHECK_REPORT.json)")


if __name__ == "__main__":
    main()
