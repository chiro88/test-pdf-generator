#!/usr/bin/env python3
"""Unified RTM Factory CLI entrypoint (D5.5).

    python rtm_cli.py generate --out rtm_gallery
    python rtm_cli.py generate-case --case-id core_figure_caption_bottom --out artifacts/rtm_case --json
    python rtm_cli.py generate-case --scenario-file my_case.yaml --out artifacts/rtm_case --json
    python rtm_cli.py list-scenarios --json
    python rtm_cli.py list-templates --json
    python rtm_cli.py validate-scenario my_case.yaml --json
    python rtm_cli.py self-check --gallery rtm_gallery --json
    python rtm_cli.py promote --gallery rtm_gallery --out rtm_frozen --keep a,b --json
    python rtm_cli.py compare --truth-root rtm_frozen --detected detected.json --out artifacts/rtm_compare --json
    python rtm_cli.py overlay --truth-root rtm_frozen --detected detected.json \
        --compare-report artifacts/rtm_compare/compare_report.json --out artifacts/rtm_overlay --json

Exit: 0 ok · 1 validation/comparison failed · 2 invalid input · 3 internal failure.
"""
import sys

from rtm_factory.cli import main

if __name__ == "__main__":
    sys.exit(main())
