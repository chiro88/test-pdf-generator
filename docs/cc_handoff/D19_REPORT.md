[D19 real-PDF operator feedback loop report]

Goal (per GPT): a review-artifact-based operator feedback **schema** (not a web
editor) that lets a human mark per-object accept/issue on a real-PDF detection and
turns that into the next detector-improvement tasks. No detector tuning.

## 1. Summary
- review schema: `real-pdf-review-v0` (YAML or JSON) — per-object `decision`
  (+ optional `expected_change` bbox) and a top-level `missed_objects` list.
- CLI: `tools/summarize_review_feedback.py` (`--review`, `--detected`, `--out`,
  `--json`) → `review_summary.json` (counts + recommended next tasks).
- docs: `docs/review/REAL_PDF_OPERATOR_REVIEW.md` (end-to-end loop).

## 2. Files changed
- `picker_cmc_v1/detector/review_feedback.py` (NEW) — schema, `object_id`
  helpers, `build_review_template()`, `load_review()` (YAML/JSON),
  `validate_review()`, `summarize()`.
- `picker_cmc_v1/tools/summarize_review_feedback.py` (NEW) — thin CLI.
- `picker_cmc_v1/detector/review_artifacts.py` — emit `review_result.template.yaml`
  (pre-filled `decision: accept`) and add `object_id` + `decision` columns to
  `review_index.md`. (Review harness only — detector algorithm untouched.)
- `docs/review/REAL_PDF_OPERATOR_REVIEW.md` (NEW).
- `tests/test_real_pdf_review_feedback_d19.py` (NEW, 9).

## 3. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_smoke/dp_sample1 --json`
  → produces `review_result.template.yaml` with object_ids figure:3-3:page1 … table:3-1:page2
- `python tools/summarize_review_feedback.py --review review_result.yaml
   --detected …/detected_manifest.json --out …/review_summary.json --json`
- `python -m pytest tests picker_cmc_v1 -q` → **172 passed**

## 4. Review workflow
- review_index fields: per-object `object_id` (`<figure|table>:<index>:page<N>`),
  caption/body/context regions, crop link, and a `decision` column to fill.
- review_result schema (`real-pdf-review-v0`):
  - `objects[]`: `object_id`, `decision` ∈ {accept, false_positive, missed_object,
    bad_caption_region, bad_body_region, bad_context_region, wrong_title,
    wrong_index, common_region_issue}, optional `expected_change` (corrected
    caption/body/context bbox), `notes`.
  - `missed_objects[]`: `kind`, `page`, `index`, `title`, `approximate_region`.
- summary output: `{ok, reviewed_objects, accepted, missed_objects, issues{…},
  recommended_next_tasks[]}`. Each issue type maps to a concrete next task.

## 5. Validation
- tests (9): valid review passes; invalid object_id rejected; unknown decision
  rejected; unknown (not-in-detected) object_id rejected; missed_object accepted;
  summary counts decisions; recommended_next_tasks generated; CLI `--json` is pure
  JSON; CLI structured error (`INVALID_REVIEW`, exit 2); no user PDF committed.
- sample feedback (dp_sample1, 1 figure flagged `bad_body_region` + 1 missed table):
  `{reviewed_objects: 4, accepted: 3, missed_objects: 1, issues:{bad_body_region:1,
  missed_object:1, …}, recommended_next_tasks:["Improve body_region inference …",
  "Improve anchor recall for missed figures/tables."]}`.

## 6. Did not touch
- detector algorithm: unchanged (pipeline/anchors/region/common-region/title untouched)
- rtm_frozen: unchanged (regression: 47/49, 100/100, 206/210)
- truth schema: unchanged
- compare tolerance: unchanged
- real PDF fixtures: none committed (user PDFs stay local; `pdf/`, `artifacts/` ignored)

## 7. Known limitations
- not a web editor yet: the schema is the contract a future editor will share;
  review is authored by editing YAML/JSON.
- no automatic correction application: `expected_change` and `recommended_next_tasks`
  are recommendations for the detector backlog, not auto-applied changes.
- a real PDF is never treated as golden truth.

Commit on `picker-cmc-d03`. Stopping after D19 report per instruction.
