[D21 detector milestone closeout report]

Documentation-only milestone: close the D11→D20.5 detector work and hand off to the
next product stage (web editor / setup-YAML / server). No detector logic or RTM
asset changes.

## 1. Summary
- docs added: detector closeout, regression commands, real-PDF review workflow,
  detector-output-v0 contract, web-editor handoff (under `docs/detector/`).
- detector milestone status: **closed at D20.5** (RTM stable; real-PDF body/anchor
  usable; only the watermark limitation remains).
- next product milestone: web editor / setup-YAML / save-manifest integration.

## 2. Files changed
- `docs/detector/DETECTOR_MILESTONE_CLOSEOUT_D11_D20_5.md` (NEW)
- `docs/detector/DETECTOR_REGRESSION_COMMANDS.md` (NEW)
- `docs/detector/REAL_PDF_REVIEW_WORKFLOW.md` (NEW)
- `docs/detector/DETECTOR_OUTPUT_V0_CONTRACT.md` (NEW)
- `docs/detector/WEB_EDITOR_HANDOFF.md` (NEW)
- `docs/cc_handoff/D21_REPORT.md` (this)
- No code, no rtm_frozen, no scenarios, no truth, no tolerance changes.

## 3. Commands run
- (re-verification only) `python -m pytest tests picker_cmc_v1 -q` → 185 passed
- RTM regression runner (unchanged numbers, see §4)

## 4. Accepted metrics
- RTM frozen: 49 cases, objects **100/100**, missing **0**, extra **0**, regions
  **206/210** (residual 4 = rotated/morph/image-like watermark limitation).
- real PDF Gate C: `dp_sample` 3 figures / 3 tables, `dp_sample1` 3 figures / 1 table;
  operator visual review after D20.5 = **10/10 accept**, 0 bad_body_region.
- pytest: **185 passed**.

## 5. Contracts documented
- detector-output-v0: `DETECTOR_OUTPUT_V0_CONTRACT.md` (manifest shape, validation,
  PDF-pt/top-left coordinates, table group/continuation).
- review feedback: `real-pdf-review-v0` summarized in `REAL_PDF_REVIEW_WORKFLOW.md`
  and `WEB_EDITOR_HANDOFF.md` (operator decisions + summary → next tasks).
- real-PDF review package: `run_detector_on_pdf.py` outputs (manifest, overlays,
  crops, review_index, template) documented in the workflow doc.
- regression commands: `DETECTOR_REGRESSION_COMMANDS.md` (pytest + RTM runner + floors).

## 6. Known limitations
- Rotated / morph / image-like watermark bbox is not PDF-derivable (the 4 RTM regions).
- Semantic waveform/table interpretation is out of scope (geometry/structure only).
- A real PDF result is a visual-review proposal, not golden truth.
- The web editor must allow manual correction; the detector result is an editable
  initial proposal.

## 7. Did not touch
- detector algorithm: unchanged
- rtm_frozen: unchanged
- RTM scenarios: unchanged
- compare tolerance: unchanged
- truth schema: unchanged

## 8. Recommended next milestone
- Web editor / setup-YAML / save-manifest integration, consuming
  `detector-output-v0` as an editable proposal and saving operator edits as
  `real-pdf-review-v0`. See `docs/detector/WEB_EDITOR_HANDOFF.md`.

Commit on `picker-cmc-d03`. Detector milestone D11→D20.5 closed; stopping after D21 report.
