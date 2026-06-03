#!/usr/bin/env python3
"""D22: emit a commented setup-yaml-v0 template.

    python tools/make_setup_template.py --out setup.yaml [--template default]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

from setup.errors import SetupError  # noqa: E402
from setup.template import render_template  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Emit a setup-yaml-v0 template (D22).")
    ap.add_argument("--out", default=None, help="write the template here (default: stdout)")
    ap.add_argument("--template", default="default", help="template name")
    args = ap.parse_args(argv)
    try:
        text = render_template(args.template)
    except SetupError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
