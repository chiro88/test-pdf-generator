# setup-yaml-v0

The product input contract: a user-authored YAML that points the detector at a PDF
and supplies document hints. Implemented in `picker_cmc_v1/setup/`.

## Generate a template

```bash
python tools/make_setup_template.py --out setup.yaml        # commented template
```

User-facing values are at the top (project / input / document_hints); fine tuning
is at the bottom (`advanced_fine_tuning`). Placeholders are the literal `CHANGE_ME`.

## Shape

```yaml
schema_version: setup-yaml-v0
project:
  name: CHANGE_ME
input:
  pdf_path: CHANGE_ME
  # page_range: "1-5"            # optional
document_hints:
  title_patterns:
    figure: { labels: ["Figure","Fig.","FIGURE"], examples: [ ... ] }
    table:  { labels: ["Table"], examples: [ ... ] }
  header:    { enabled: true, may_have_two_lines: true, even_odd_mirrored: true }
  footer:    { enabled: true, may_have_rule_bar: true, may_have_page_number: true }
  watermark: { enabled: true, expected_text_examples: ["Licensed to","CONFIDENTIAL","DRAFT"] }
output:
  artifact_dir: artifacts/picker_run
  save_manifest_path: artifacts/picker_run/editor_save_manifest.json
advanced_fine_tuning:
  coordinate_unit: pdf_pt
  coordinate_origin: top-left
  detector_profile: default
```

## Required fields

`schema_version`, `project.name`, `input.pdf_path`, `output.artifact_dir`.
`project.name` and `input.pdf_path` must be resolved away from `CHANGE_ME`.

`document_hints` is advisory for v0 (the detector's anchors/common-region logic is
already robust); it is carried for forward compatibility and future tuning.

## Error codes

| code | when |
|---|---|
| `SETUP_FILE_NOT_FOUND` | the setup path does not exist |
| `SETUP_FILE_UNREADABLE` | not readable / not valid YAML / root not a mapping |
| `SETUP_MISSING_FIELD` | a required field is **absent** |
| `SETUP_PLACEHOLDER_UNRESOLVED` | a `CHANGE_ME` placeholder was left in |
| `SETUP_INVALID_VALUE` | a field is **present** but has a bad value |
| `SETUP_BAD_PAGE_RANGE` | `input.page_range` malformed (e.g. `"5-2"`) |
| `SETUP_UNKNOWN_DETECTOR` | `advanced_fine_tuning.detector_profile` unknown |
| `SETUP_UNKNOWN_TEMPLATE` | requested template name unknown |

`SETUP_MISSING_FIELD` is for an absent field only; a present-but-wrong field is
`SETUP_INVALID_VALUE`.

## Run the detector from a setup file

```bash
python tools/run_detector_with_setup.py --setup setup.yaml --json
```

Loads + validates the setup, runs the no-truth detector on `input.pdf_path`, and
writes (under `output.artifact_dir`):
- `detected_manifest.json` — `detector-output-v0` (the editable initial proposal)
- the initial `editor-save-manifest-v0` at `output.save_manifest_path`

No correctness claim is made for a real PDF (see the detector closeout docs).
