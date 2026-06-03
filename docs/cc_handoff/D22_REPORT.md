[D22 setup YAML + save-manifest contract report]

The product contract layer before the web editor: a user-authored `setup-yaml-v0`
in, a `detector-output-v0` proposal, and an `editor-save-manifest-v0` corrected
output. No web UI / server, no detector tuning, no RTM/truth/tolerance change.

## 1. Summary
- setup YAML: `setup-yaml-v0` schema + commented template + loader + validator +
  stable error codes.
- editor save manifest: `editor-save-manifest-v0` schema + builder (proposal →
  editable) + append-only edit log + validator.
- detector setup runner: `run_detector_with_setup.py` (setup → detect → manifests).

## 2. Files changed
- `picker_cmc_v1/setup/` (NEW): `errors.py`, `schema.py`, `template.py`, `loader.py`,
  `validator.py`, `__init__.py`
- `picker_cmc_v1/editor_manifest/` (NEW): `schema.py`, `validator.py`, `writer.py`, `__init__.py`
- `picker_cmc_v1/tools/` (NEW): `make_setup_template.py`, `run_detector_with_setup.py`,
  `validate_editor_manifest.py`
- `docs/product/` (NEW): `SETUP_YAML_V0.md`, `EDITOR_SAVE_MANIFEST_V0.md`, `PRODUCT_PIPELINE_D22.md`
- `tests/test_setup_yaml_d22.py` (8), `tests/test_editor_manifest_d22.py` (5)
- detector / rtm_frozen / truth / tolerance: untouched.

## 3. Commands run
- `python tools/make_setup_template.py --out setup.yaml`
- `python tools/run_detector_with_setup.py --setup setup.yaml --json`
- `python tools/validate_editor_manifest.py --manifest editor_save_manifest.json --json`
- `python -m pytest tests picker_cmc_v1 -q` → **198 passed**; RTM regression unchanged.

## 4. Setup YAML contract
- template: `make_setup_template.py` emits commented YAML (user values on top,
  `advanced_fine_tuning` at the bottom; `CHANGE_ME` placeholders).
- parser: `setup/loader.py` (file → mapping).
- validation: `setup/validator.py` — required fields, placeholder resolution,
  page-range, coordinate unit/origin, detector profile.
- error codes: `SETUP_FILE_NOT_FOUND`, `SETUP_FILE_UNREADABLE`, `SETUP_MISSING_FIELD`
  (absent only), `SETUP_PLACEHOLDER_UNRESOLVED`, `SETUP_INVALID_VALUE`
  (present-but-wrong), `SETUP_BAD_PAGE_RANGE`, `SETUP_UNKNOWN_DETECTOR`,
  `SETUP_UNKNOWN_TEMPLATE`.

## 5. Editor save manifest contract
- schema: `editor-save-manifest-v0` — `source_pdf`, `source_detector_manifest`,
  PDF-pt/top-left, `pages[]` (post-edit state), `edits[]` (audit log).
- edit log: append-only; `apply_bbox_edit` updates the region in place AND records
  `{object_id, operation, region, before, after}`.
- validator: rejects wrong coordinate unit/origin, missing sources, malformed
  pages/edits.

## 6. Detector integration
- setup → detect: `run_detector_with_setup.py` loads+validates the setup, runs the
  no-truth detector on `input.pdf_path`.
- output artifacts: `<artifact_dir>/detected_manifest.json` (detector-output-v0, the
  editable proposal) + the initial `editor-save-manifest-v0` at `save_manifest_path`.

## 7. Tests
- setup (8): template has comments/placeholders; valid parse; missing pdf_path →
  MISSING_FIELD; missing file → FILE_NOT_FOUND; bad YAML → FILE_UNREADABLE;
  unedited placeholder → PLACEHOLDER_UNRESOLVED; bad profile → UNKNOWN_DETECTOR;
  bad page range → BAD_PAGE_RANGE; runner emits valid detector-output-v0.
- editor manifest (5): valid accepted; wrong coordinate origin/unit rejected; bbox
  edit logged + applied; malformed edit rejected.
- full suite: **198 passed**. RTM regression unchanged (47/49, 100/100, 206/210).

## 8. Did not touch
- detector algorithm: unchanged
- rtm_frozen: unchanged
- RTM scenarios: unchanged
- compare tolerance: unchanged
- web UI / server: not started

## 9. Known limitations
- `document_hints` is advisory for v0 (carried for forward-compat; the detector is
  already robust); not yet wired into detector tuning.
- Real-PDF output remains a visual-review proposal, never golden truth.
- No web UI/server yet — this is the contract foundation they will consume.

Commit on `picker-cmc-d03`. Stopping after D22 report.
