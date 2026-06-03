"""setup-yaml-v0 schema constants (D22)."""
from __future__ import annotations

SCHEMA_VERSION = "setup-yaml-v0"
PLACEHOLDER = "CHANGE_ME"

# Required fields as dotted paths (absent -> SETUP_MISSING_FIELD).
REQUIRED_FIELDS = (
    "schema_version",
    "project.name",
    "input.pdf_path",
    "output.artifact_dir",
)

# Fields the user MUST resolve away from the CHANGE_ME placeholder.
PLACEHOLDER_FIELDS = ("project.name", "input.pdf_path")

VALID_DETECTOR_PROFILES = ("default",)
VALID_COORDINATE_UNITS = ("pdf_pt",)
VALID_COORDINATE_ORIGINS = ("top-left",)

# Named setup templates make_setup_template can emit.
KNOWN_TEMPLATES = ("default",)
