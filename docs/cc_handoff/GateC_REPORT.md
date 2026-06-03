[Gate C real-PDF operator review package report]

Packaging only — no code changes, no detector tuning. Built with the existing
D17 (`run_detector_on_pdf.py`) and D19 (review template) tooling.

## 1. Summary
- PDFs processed: `dp_sample.pdf`, `dp_sample1.pdf` (local, NOT committed)
- package path: `picker_cmc_v1/artifacts/real_pdf_review_gate_c/` (git-ignored)
  bundled as `GateC_real_pdf_review_package.tar.gz` (1.6 MB, 34 entries, 18 PNGs)
- detected objects: **10** total (dp_sample 6, dp_sample1 4) — see `GATE_C_OBJECT_LIST.csv`

## 2. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample.pdf  --out artifacts/real_pdf_review_gate_c/dp_sample  --json`
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_review_gate_c/dp_sample1 --json`
- assembled `GATE_C_OBJECT_LIST.csv` (from the two detected_manifest.json) and
  `GATE_C_REVIEW_INSTRUCTIONS.md`; bundled into `GateC_real_pdf_review_package.tar.gz`

## 3. dp_sample result
- pages: 6
- figures: 3
- tables: 3
- common regions: 43 (incl. 3 watermarks — the diagonal "Licensed to …" mark)
- warnings: none

## 4. dp_sample1 result
- pages: 2
- figures: 3   (ARM no-colon captions: Figure 3-3 / 3-4 / 3-5)
- tables: 1    (Table 3-1)
- common regions: 11
- warnings: none

## 5. Review artifacts
- review_index: `dp_sample/review_index.md`, `dp_sample1/review_index.md`
  (per-object table with `object_id` + `decision` column)
- review_result.template: `dp_sample*/review_result.template.yaml`
  (pre-filled `decision: accept`, ready to edit)
- object list CSV: `GATE_C_OBJECT_LIST.csv` — columns: pdf, page, object_id, kind,
  index, title, caption_region, body_region, context_region, crop_path, decision
  (**decision left blank for the human reviewer**); 10 rows
- overlays: `dp_sample/pages/*.png` (6), `dp_sample1/pages/*.png` (2)
- crops: `dp_sample/crops/*.png` (6), `dp_sample1/crops/*.png` (4)

## 6. Did not touch
- detector algorithm: unchanged
- rtm_frozen: unchanged
- truth schema: unchanged
- compare tolerance: unchanged
- real PDF committed: no (source PDFs and rendered artifacts are git-ignored;
  only this report is committed)

## 7. Next required actor
- **human / GPT reviewer** opens the package and fills the `decision` values
  (CSV column or per-PDF `review_result.yaml`), lists any `missed_objects`, then
  runs `summarize_review_feedback.py` to produce the next detector tasks.

Stopping after Gate C package report per instruction.
