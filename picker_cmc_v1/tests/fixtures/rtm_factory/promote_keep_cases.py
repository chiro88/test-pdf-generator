#!/usr/bin/env python3
"""CLI: promote human-kept RTM gallery cases into the frozen fixture set (D3).

Default behaviour is index.md driven:

    python promote_keep_cases.py --gallery ../rtm_gallery --out ../rtm_frozen

Explicit override (still copy-only, still fail-safe on existing output):

    python promote_keep_cases.py --gallery ../rtm_gallery --out ../rtm_frozen \
        --keep core_fixed_header_footer,core_figure_caption_bottom

promotion success != detector pass
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rtm_factory.promote import PromotionError, promote

_FIXTURES = Path(__file__).resolve().parents[1]
DEFAULT_GALLERY = _FIXTURES / "rtm_gallery"
DEFAULT_OUT = _FIXTURES / "rtm_frozen"


def main() -> None:
    ap = argparse.ArgumentParser(description="Promote kept RTM gallery cases to the frozen fixture set.")
    ap.add_argument("--gallery", default=str(DEFAULT_GALLERY), help="source generated gallery dir")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="frozen fixture output dir")
    ap.add_argument("--keep", default=None, help="comma-separated case_ids to force-keep (overrides index.md)")
    ap.add_argument("--force", action="store_true", help="overwrite existing output dir")
    ap.add_argument("--allow-empty", action="store_true", help="permit an empty frozen set (testing)")
    args = ap.parse_args()

    keep_override = [s.strip() for s in args.keep.split(",") if s.strip()] if args.keep else None

    try:
        result = promote(
            args.gallery,
            args.out,
            keep_override=keep_override,
            force=args.force,
            allow_empty=args.allow_empty,
        )
    except PromotionError as exc:
        print(f"promotion failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"promoted {len(result['selected'])} case(s) to {result['out_dir']} "
        f"(dropped/ignored {len(result['dropped'])}, source={result['selection_source']})"
    )


if __name__ == "__main__":
    main()
