# Real-PDF review workflow

The loop that turns a real (truth-less) PDF into a human-reviewed, actionable
result. See `docs/review/REAL_PDF_OPERATOR_REVIEW.md` for the operator-facing
detail; this is the engineering summary.

```
real PDF
  → run_detector_on_pdf.py     (D17)  detected_manifest.json + review_index.md
                                       + overlays + crops + review_result.template.yaml (D19)
  → operator edits template    →       review_result.yaml   (accept / issue per object)
  → summarize_review_feedback.py(D19)  review_summary.json   (counts + next tasks)
  → next detector task
```

## 1. Produce the review package

```bash
# from picker_cmc_v1/
python tools/run_detector_on_pdf.py --pdf /path/to/input.pdf \
    --out artifacts/real_pdf_smoke/<name> --json
```

Outputs under `<out>/`:
- `detected_manifest.json` — `detector-output-v0` (validated)
- `summary.json` — counts (`figures_detected`, `tables_detected`, …)
- `review_index.md` — per-object table (object_id + decision column)
- `review_result.template.yaml` — pre-filled `decision: accept` skeleton
- `pages/page_NNN_overlay.png` — detected regions drawn on each page
- `crops/<figure|table>_<index>_body.png` — body crop per object

Invalid PDF path → `{"ok": false, "error_code": "INVALID_PDF_INPUT"}` (exit 2).

## 2. Operator review

Copy the template to `review_result.yaml`, set each object's `decision`
(`accept` / `bad_body_region` / `false_positive` / …), list any `missed_objects`,
optionally add `expected_change` bbox proposals. `object_id` is
`"<figure|table>:<index>:page<N>"`.

## 3. Summarize into next tasks

```bash
python tools/summarize_review_feedback.py \
    --review review_result.yaml \
    --detected artifacts/real_pdf_smoke/<name>/detected_manifest.json \
    --out artifacts/real_pdf_smoke/<name>/review_summary.json --json
```

Output: `{ok, reviewed_objects, accepted, missed_objects, issues{…},
recommended_next_tasks[]}`.

## Gate C status (current)

| PDF | figures | tables | review after D20.5 |
|---|---|---|---|
| dp_sample.pdf | 3 | 3 | accept |
| dp_sample1.pdf | 3 | 1 | accept |

10/10 objects accept (operator visual review). Note: this is a visual proposal,
not a correctness guarantee for arbitrary real PDFs.

## Rules

- The detector never reads truth; a real PDF is never treated as golden truth.
- **User / copyrighted PDFs and rendered artifacts are NOT committed** (`pdf/` and
  `artifacts/` are git-ignored). Only reports/summaries are committed.
