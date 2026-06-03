"""downstream-package-v0 schema constants (D27).

A standard, geometry-only object package for downstream waveform/diagram/table LLM
tools. It carries the human-edited bboxes + per-object crops; it does NOT interpret
content. ``downstream_task_hint`` is a structural routing hint only (figure ->
diagram/waveform, table -> table), not a semantic claim.
"""
from __future__ import annotations

SCHEMA_VERSION = "downstream-package-v0"
COORDINATE_UNIT = "pdf_pt"
COORDINATE_ORIGIN = "top-left"

REGIONS = ("caption", "body", "context")          # crop keys
KINDS = ("figure", "table")

# Structural routing hint (NOT semantic interpretation).
TASK_HINTS = {"figure": "diagram_or_waveform", "table": "table"}
