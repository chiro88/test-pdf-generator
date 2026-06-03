[D28 product end-to-end smoke / RC closeout report]

One end-to-end smoke validates the whole product flow, plus release-candidate docs.
No new features, no detector tuning, no schema changes.

## 1. Summary
- e2e smoke: `tools/run_product_e2e_smoke.py` (+ `run_e2e()`), exercises setup →
  detector → editor manifest → edit → save → reopen → edited review export →
  downstream package, validating each stage.
- docs: product quickstart, RC checklist, artifact-contracts summary.
- RC status: all gates green — pytest **252 passed**, RTM unchanged, e2e all stages ✓.

## 2. Files changed
- `picker_cmc_v1/tools/run_product_e2e_smoke.py` (NEW): `run_e2e(pdf, workdir)` + CLI.
- `docs/product/PRODUCT_E2E_QUICKSTART.md` (NEW)
- `docs/product/PRODUCT_RELEASE_CANDIDATE_CHECKLIST.md` (NEW)
- `docs/product/ARTIFACT_CONTRACTS_SUMMARY.md` (NEW)
- `tests/test_product_e2e_smoke_d28.py` (4)
- detector / setup schema / editor-manifest schema / downstream-package schema /
  rtm_frozen / tolerance / web UI: untouched (smoke only composes existing tools).

## 3. Commands run
- `python tools/run_product_e2e_smoke.py --pdf <pdf> --workdir <dir> --json`
- `python -m pytest tests picker_cmc_v1 -q` → **252 passed**; RTM regression unchanged.

## 4. E2E flow verified
- setup: template generated, filled, validated (`setup-yaml-v0`).
- detector: `run_from_setup` → `detected_manifest.json` + `editor_save_manifest.json`.
- editor manifest: `validate_manifest` PASS (`editor-save-manifest-v0`).
- edit/save/reload: one `body_region` edit via `edit_bbox` + `save`; reopen keeps it.
- edited artifact export: `edited-review-v0` overlays + crops from the edited bboxes.
- downstream package: `downstream-package-v0` with `objects.jsonl`; provenance
  (`source_editor_manifest`) → the editor manifest, not the detector output.

## 5. Validation
- pytest: **252 passed**.
- RTM regression: cases 47/49, objects 100/100, missing 0, extra 0, regions 206/210
  (4 = documented watermark limitation) — unchanged.
- manifest validators: setup-yaml-v0, editor-save-manifest-v0 PASS in the e2e flow.
- package validator: downstream-package-v0 PASS; provenance check enforced.

## 6. Artifact outputs (per run dir)
- detected_manifest: `detected_manifest.json` (detector-output-v0)
- editor_save_manifest: `editor_save_manifest.json` (editor-save-manifest-v0)
- edited_review: `edited_review/{summary.json,index.md,pages/*.png,crops/*.png}`
- downstream_package: `downstream_package/{package_manifest.json,objects.jsonl,index.md,crops/*.png}`

## 7. Did not touch
- detector: unchanged
- schemas: unchanged (setup / detector-output / editor-manifest / downstream-package)
- rtm_frozen: unchanged
- compare tolerance: unchanged
- semantic interpretation: none added

## 8. Known limitations
- rotated/morph/image-like watermark bbox: documented limitation (4 RTM regions).
- real PDF: operator visual-review proposal, not golden truth.
- no semantic interpretation / no LLM calls (the downstream package is the hand-off).
- local single-user web server (no auth/sessions/DB/cloud/multi-user).

Commit on `picker-cmc-d03`. Stopping after D28 report. Release-candidate flow is
green end-to-end.
