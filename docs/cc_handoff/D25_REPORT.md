[D25 edit persistence + post-edit artifact export report]

Closes the correction loop: a saved/Save-As manifest reopens with the edited bboxes,
and post-edit overlays/crops are exported from that SAVED editor-save-manifest-v0
(source of truth — no fresh detector run). Detector and contracts untouched.

## 1. Summary
- reload: `load_run` reopens the default `editor_save_manifest.json` with edits applied.
- save-as reopen: `run_web_editor.py --manifest <path>` opens an explicit saved
  manifest (must validate + live inside the run dir).
- export artifacts: `export_editor_manifest_artifacts.py` builds overlays/crops/index/
  summary from the edited manifest.

## 2. Files changed
- `picker_cmc_v1/web_editor/models.py`: `load_run(run_dir, manifest_path=None)` —
  explicit manifest path, validated, with a `MANIFEST_OUTSIDE_RUN_DIR` policy guard;
  `save_path` follows the opened manifest.
- `picker_cmc_v1/web_editor/export.py` (NEW): `export_artifacts` (overlays + body
  crops + index + summary, `edited-review-v0`) from the saved manifest.
- `picker_cmc_v1/tools/export_editor_manifest_artifacts.py` (NEW): export CLI.
- `picker_cmc_v1/tools/run_web_editor.py`: `--manifest` flag.
- `docs/product/WEB_EDITOR_V0.md`: D25 section.
- `tests/test_web_editor_persistence_d25.py` (9 functions / 10 checks).
- detector / setup schema / editor-manifest schema / rtm_frozen / tolerance: untouched.

## 3. Commands run
- `python tools/run_web_editor.py --run-dir <dir> --manifest <dir>/versions/edited.json`
- `python tools/export_editor_manifest_artifacts.py --manifest <dir>/versions/edited.json --out <dir>/edited_review --json`
- `python -m pytest tests picker_cmc_v1 -q` → **227 passed**; RTM regression unchanged.

## 4. Persistence behavior
- default manifest: `run-dir/editor_save_manifest.json` (Save overwrites it).
- explicit manifest: `--manifest <path>`; validated before serving; the object tree,
  overlays, and PNG all use the saved/edited state.
- edit log: preserved across save → reload (append-only `edits[]`).
- reload validation: an invalid explicit manifest → `RUN_MANIFEST_INVALID`; a path
  outside the run dir → `MANIFEST_OUTSIDE_RUN_DIR`.

## 5. Export behavior
- overlay: `pages/page_NNN_overlay.png` drawn from the manifest's edited bboxes.
- crops: `crops/<figure|table>_<index>_body_region.png` cropped at the edited bbox.
- summary: `summary.json` (`edited-review-v0`, includes `edit_count`) + `index.md`.
- source manifest: the **editor-save-manifest-v0** is the source of truth — the
  exporter never re-runs the detector.

## 6. Validation
- tests (9 fns / 10 checks): edit→save→reload persists; edit→save-as→`--manifest`
  reopen persists; edit log preserved; overlay reflects reloaded bbox; export builds
  index/summary/overlay/crop; exported crop uses the edited bbox (not the detector
  original); invalid explicit manifest rejected; manifest-outside-run-dir rejected;
  page PNG works after reload; RTM frozen body unchanged.
- sample edit/reload/export: synthetic PDF — edit `body_region` to `[120,118,480,205]`,
  Save + Save-As `versions/edited.json`, reopen via `--manifest` (bbox persists),
  export → crop `body_region == [120,118,480,205]`, `edit_count == 1`.
- sample artifact paths: `edited_review/{index.md, summary.json, pages/*.png, crops/*.png}`.

## 7. Did not touch
- detector: unchanged
- setup schema: unchanged
- editor manifest schema: unchanged (no breaking change)
- rtm_frozen: unchanged
- compare tolerance: unchanged

## 8. Known limitations
- no undo/redo
- no multi-user / sessions
- no database (file-backed manifest only)

Commit on `picker-cmc-d03`. Stopping after D25 report.
