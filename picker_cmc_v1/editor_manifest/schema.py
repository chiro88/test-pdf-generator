"""editor-save-manifest-v0 schema constants (D22).

The web editor's final saved artifact: a human-corrected candidate derived from
the detector's initial proposal. Coordinates stay PDF-pt / top-left, and edits are
kept as an append-only log (never just an in-place mutation).
"""
from __future__ import annotations

SCHEMA_VERSION = "editor-save-manifest-v0"
COORDINATE_UNIT = "pdf_pt"
COORDINATE_ORIGIN = "top-left"

# Edit operations the editor may record.
OPERATIONS = (
    "update_bbox",      # move/resize a region of an existing object
    "update_field",     # change a non-region field (title, index, ...)
    "add_object",       # operator added a missed figure/table
    "remove_object",    # operator removed a false-positive object
)

REGION_NAMES = ("caption_region", "body_region", "context_region", "bbox")
