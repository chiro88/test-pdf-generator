"""setup-yaml-v0 commented template (D22).

The template is emitted as commented YAML: user-facing values at the top
(project / input / document_hints), fine tuning at the bottom. Placeholders are
the literal CHANGE_ME so the validator can reject an unedited template.
"""
from __future__ import annotations

from .errors import SetupError
from .schema import KNOWN_TEMPLATES

_DEFAULT_TEMPLATE = """\
# picker_cmc setup (setup-yaml-v0)
# Fill the CHANGE_ME values. Everything under advanced_fine_tuning has sane
# defaults and can usually be left as-is.
schema_version: setup-yaml-v0

project:
  name: CHANGE_ME                      # a label for this run

input:
  pdf_path: CHANGE_ME                  # path to the PDF to process
  # page_range: "1-5"                  # optional: pages to process, e.g. "1-5" or "3"

document_hints:
  # Caption title forms the detector should expect (examples improve recall).
  title_patterns:
    figure:
      labels: ["Figure", "Fig.", "FIGURE"]
      examples:
        - "Figure 3-3 Read transfer with two wait states"
        - "Figure 1-1: Example diagram"
    table:
      labels: ["Table"]
      examples:
        - "Table 3-1 Transfer type encoding"

  header:
    enabled: true
    may_have_two_lines: true
    even_odd_mirrored: true

  footer:
    enabled: true
    may_have_rule_bar: true
    may_have_page_number: true

  watermark:
    enabled: true
    expected_text_examples:
      - "Licensed to"
      - "CONFIDENTIAL"
      - "DRAFT"

output:
  artifact_dir: artifacts/picker_run            # where detector/review artifacts go
  save_manifest_path: artifacts/picker_run/editor_save_manifest.json

advanced_fine_tuning:
  coordinate_unit: pdf_pt              # contract: PDF points
  coordinate_origin: top-left         # contract: top-left origin
  detector_profile: default           # detector configuration profile
"""

_TEMPLATES = {"default": _DEFAULT_TEMPLATE}


def render_template(name: str = "default") -> str:
    """Return the commented setup YAML template text for ``name``."""
    if name not in KNOWN_TEMPLATES or name not in _TEMPLATES:
        raise SetupError("SETUP_UNKNOWN_TEMPLATE", f"unknown setup template {name!r}", field="template")
    return _TEMPLATES[name]
