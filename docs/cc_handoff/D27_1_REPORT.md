[D27.1 downstream package provenance fix report]

Fix the blocking provenance bug: the package's `source_editor_manifest` recorded the
detector output (`detected_manifest.json`) instead of the editor-save-manifest. The
package must trace to the human-edited final state. No semantic interpretation; no
package schema change.

## 1. Summary
- source_editor_manifest fix: `build_package` now records the actual
  editor-save-manifest path (passed as `source_manifest_path`), never the detector
  manifest.
- validator/test hardening: the exporter validates the input is
  `editor-save-manifest-v0`; the package validator rejects a `source_editor_manifest`
  pointing at `detected_manifest.json`.

## 2. Files changed
- `picker_cmc_v1/downstream_package/exporter.py`: `build_package(..., source_manifest_path)`
  required; input schema check (`editor-save-manifest-v0`); `source_editor_manifest` =
  that path; summary + index name the editor manifest.
- `picker_cmc_v1/downstream_package/validator.py`: provenance guard (reject
  `detected_manifest.json` as the source).
- `picker_cmc_v1/tools/export_downstream_package.py`: pass `source_manifest_path=--manifest`.
- `picker_cmc_v1/web_editor/server.py`: pass `source_manifest_path=ctx.manifest_path`.
- `tests/test_downstream_package_provenance_d271.py` (5) NEW; updated D27 test calls.

## 3. Commands run
- `python tools/export_downstream_package.py --manifest <editor_save_manifest.json> --out <dir> --json`
- `python -m pytest tests picker_cmc_v1 -q` → **248 passed**; RTM regression unchanged.

## 4. Contract correction
- before: `"source_editor_manifest": "detected_manifest.json"` (detector proposal — wrong).
- after: `"source_editor_manifest": ".../editor_save_manifest.json"` (the edited manifest).
- CLI export: records `--manifest` (the editor-save-manifest path).
- web export: records `ctx.manifest_path` (the run's editor-save-manifest).
- Additionally: exporting a detector-output manifest as input now raises `ExportError`
  (`input must be editor-save-manifest-v0`).

## 5. Validation
- tests (5 new + D27 updated): CLI records the editor manifest (not detector);
  validator rejects detector-output provenance; objects/crops still use the edited
  bbox; web export records the editor manifest + validates; a detector-output input
  is rejected.
- sample package_manifest: `source_editor_manifest` ends with
  `editor_save_manifest.json`; `index.md` names the editor-save-manifest-v0 source.
- edited bbox crop check: a figure body edited to `[110,108,490,210]` exports that
  bbox + crop (unchanged from D27).

## 6. Did not touch
- detector: unchanged
- setup schema: unchanged
- editor manifest schema: unchanged
- rtm_frozen: unchanged
- compare tolerance: unchanged
- semantic interpretation: not added (still geometry/crops only)

## 7. Known limitations
- no semantic interpretation (waveform/table content not parsed)
- no LLM call (the package is the hand-off)

Commit on `picker-cmc-d03`. Stopping after D27.1 report.
