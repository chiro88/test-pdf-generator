[D29 RC packaging / operator handoff report]

Documentation/packaging closeout so a new operator can run the whole flow from a
fresh checkout. No code features, no detector tuning, no schema changes.

## 1. Summary
- docs: operator handoff, RC final sign-off, troubleshooting (under `docs/product/`),
  plus a `requirements.txt` and a README product pointer.
- install/run path: `pip install -r requirements.txt` → one-command E2E smoke →
  setup → web editor → export.
- RC status: all gates green; recommendation **TAG RC**.

## 2. Files changed
- `requirements.txt` (NEW): PyMuPDF + PyYAML (+ pytest for tests); server is stdlib.
- `docs/product/OPERATOR_HANDOFF.md` (NEW): fresh-checkout install → setup → edit → export.
- `docs/product/RC_FINAL_SIGNOFF.md` (NEW): the release gate + milestone status.
- `docs/product/TROUBLESHOOTING.md` (NEW): error codes + common fixes.
- `README.md`: product pointer to the operator handoff.
- No code, schema, detector, rtm_frozen, tolerance, or web-feature changes.

## 3. Commands run
- `pip install -r requirements.txt` then `python -c "import fitz, yaml"` → deps ok
- `python tools/run_product_e2e_smoke.py --pdf <pdf> --workdir <dir> --json` → 9/9 ✓
- `python -m pytest tests picker_cmc_v1 -q` → 252 passed; RTM regression unchanged

## 4. Operator workflow (documented)
- setup template: `tools/make_setup_template.py --out setup.yaml` (fill CHANGE_ME)
- detector run: `tools/run_detector_with_setup.py --setup setup.yaml`
- web editor: `tools/run_web_editor.py --setup setup.yaml --port 8765` (or `--run-dir`)
- edit/save: select object → region → drag/resize → Save / Save As; Ruler; Export package
- downstream package: `tools/export_downstream_package.py --manifest editor_save_manifest.json --out …`

## 5. Validation
- pytest: 252 passed.
- RTM regression: cases 47/49, objects 100/100, missing 0, extra 0, regions 206/210
  (4 = documented watermark limitation) — unchanged.
- E2E smoke: all 9 stages ✓ (setup → … → downstream package + provenance).

## 6. Hygiene
- user PDFs: not committed (`pdf/` git-ignored).
- artifacts: not committed (`artifacts/`, run dirs git-ignored).
- generated files: only source, tests, reports, and docs are committed; `requirements.txt`
  added.

## 7. Did not touch
- detector: unchanged
- schemas: unchanged (all seven contracts)
- rtm_frozen: unchanged
- compare tolerance: unchanged
- web features: none added (docs only)

## 8. Final recommendation
- **TAG RC.** All gates green (pytest 252, RTM unchanged, E2E 9/9), contracts frozen,
  scope boundaries and limitations documented, hygiene verified. See
  `docs/product/RC_FINAL_SIGNOFF.md`.

Commit on `picker-cmc-d03`. Stopping after D29 report.
