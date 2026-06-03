# Release-candidate checklist

Run before tagging a picker_cmc release candidate. All commands from `picker_cmc_v1/`
(tests from the repo root).

## Gates

- [ ] **Tests**: `python -m pytest tests picker_cmc_v1 -q` → all pass (**252** at D28).
- [ ] **RTM regression** (`DETECTOR_REGRESSION_COMMANDS.md`): objects **100/100**,
      missing **0**, extra **0**, cases **≥45/49** (currently 47), regions **≥200/210**
      (currently 206). The 4 region failures are the documented rotated/morph watermark
      limitation.
- [ ] **E2E smoke**: `python tools/run_product_e2e_smoke.py --pdf <pdf> --workdir <dir> --json`
      → every stage `✓`:
  - [ ] setup template generated + setup valid
  - [ ] detector run created (`detected_manifest.json`)
  - [ ] `editor_save_manifest.json` validates
  - [ ] one bbox edit applied via the edit path
  - [ ] save → reopen keeps the edit
  - [ ] edited review export (overlays + crops from edited bboxes)
  - [ ] downstream package export
  - [ ] `package_manifest.source_editor_manifest` → the editor manifest (NOT
        `detected_manifest.json`)
  - [ ] `objects.jsonl` present
- [ ] **Validators**: detector-output-v0, editor-save-manifest-v0, downstream-package-v0
      all PASS on the produced artifacts.

## Contracts (frozen for v0)

- [ ] setup-yaml-v0, detector-output-v0, editor-save-manifest-v0, edited-review-v0,
      downstream-package-v0, real-pdf-review-v0, web-editor-run-v0 unchanged
      (`ARTIFACT_CONTRACTS_SUMMARY.md`). Extend with optional fields only.

## Hygiene

- [ ] No user/copyrighted PDFs or rendered artifacts committed (`pdf/`, `artifacts/`
      are git-ignored; only reports/summaries are committed).
- [ ] Detector algorithm, `rtm_frozen`, compare tolerance, scenarios unchanged since
      the detector closeout (D20.5) unless a review explicitly re-opened them.

## Scope boundaries (NOT in this RC)

- No semantic waveform/diagram/table interpretation; no LLM calls.
- Web editor is local single-user (no auth, sessions, DB, cloud, multi-user).
- Real-PDF results are operator visual-review proposals, never golden truth.
- Rotated/morph/image-like watermark bbox is a documented limitation.

## Sign-off

| gate | status | note |
|---|---|---|
| pytest | | |
| RTM regression | | |
| E2E smoke | | |
| contracts unchanged | | |
| hygiene | | |
