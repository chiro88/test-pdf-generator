"""detector-output-v0 schema constants (D10).

This is the contract a picker_cmc detector must emit and that the RTM compare
harness consumes. It is intentionally compatible with the RTM truth region
shape (figure/table caption/body/context, table group/continuation) plus the
title_position / title_body_gap_lines fields added in D9.
"""
from __future__ import annotations

SCHEMA_VERSION = "detector-output-v0"
COORDINATE_UNIT = "pdf_pt"
COORDINATE_ORIGIN = "top-left"

COMMON_KINDS = ("header", "footer", "watermark")
FIGURE_REGIONS = ("caption_region", "body_region", "context_region")
TABLE_REGIONS = ("caption_region", "body_region", "context_region")  # context optional
TITLE_POSITIONS = ("above", "below")

# Required (non-region) fields per object.
FIGURE_FIELDS = ("index", "title", "title_position", "title_body_gap_lines")
TABLE_FIELDS = ("index", "title", "table_group_id", "part_index", "is_continuation", "continuation_marker")
PRODUCER_FIELDS = ("name", "version", "mode")
