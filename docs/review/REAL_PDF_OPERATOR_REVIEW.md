# Real-PDF operator review loop (D19)

A real PDF has **no ground truth**, so the detector's output is confirmed by a
human. This loop captures that judgement in a small, web-editor-friendly schema
(`real-pdf-review-v0`) and turns it into the next detector improvement tasks.

```
real PDF
  → run_detector_on_pdf.py        (D17) → detected_manifest.json + review_index.md + overlays/crops
                                          + review_result.template.yaml   (D19)
  → operator edits the template    → review_result.yaml   (accept / issue per object)
  → summarize_review_feedback.py   (D19) → review_summary.json  (counts + recommended next tasks)
  → next detector task
```

This is **not** a web editor and it does **not** apply corrections automatically;
it is the data contract a future editor and the detector-improvement backlog share.

## 1. Produce the review package

```bash
python tools/run_detector_on_pdf.py --pdf /path/to/input.pdf \
    --out artifacts/real_pdf_smoke/<name> --json
```

Among the outputs: `review_index.md` (per-object table, with an `object_id` and a
`decision` column to fill in) and `review_result.template.yaml` (pre-filled with
`decision: accept` for every detected object).

## 2. Operator edits the review

Copy the template to `review_result.yaml` and set each object's `decision`. The
`object_id` is `"<figure|table>:<index>:page<N>"` (e.g. `figure:3-3:page1`).

```yaml
schema_version: real-pdf-review-v0
pdf: dp_sample1.pdf
reviewer: manual
objects:
  - object_id: figure:3-3:page1
    decision: accept
    notes: "caption/body reasonable"
  - object_id: figure:3-4:page1
    decision: bad_body_region
    expected_change:
      body_region: [72, 210, 540, 330]   # optional operator-proposed bbox
    notes: "crop misses waveform lower labels"
missed_objects:                            # objects the detector did NOT emit
  - kind: table
    page: 2
    index: "3-2"
    approximate_region: [72, 300, 540, 500]
```

### Decisions

| decision | meaning |
|---|---|
| `accept` | detection is good |
| `false_positive` | not a real figure/table |
| `missed_object` | (also use the top-level `missed_objects` list) |
| `bad_caption_region` | caption band wrong |
| `bad_body_region` | body band wrong |
| `bad_context_region` | context band wrong |
| `wrong_title` | title text wrong |
| `wrong_index` | index wrong |
| `common_region_issue` | header/footer/watermark wrong |

`expected_change` (optional) lets the operator propose a corrected
`caption_region` / `body_region` / `context_region` bbox.

## 3. Summarize into next tasks

```bash
python tools/summarize_review_feedback.py \
    --review review_result.yaml \
    --detected artifacts/real_pdf_smoke/<name>/detected_manifest.json \
    --out artifacts/real_pdf_smoke/<name>/review_summary.json --json
```

```json
{
  "ok": true,
  "reviewed_objects": 4,
  "accepted": 3,
  "issues": { "bad_body_region": 1, "false_positive": 0, "missed_object": 1, ... },
  "recommended_next_tasks": [
    "Improve body_region inference for flagged figures/tables (e.g. waveform lower-bound).",
    "Improve anchor recall for missed figures/tables."
  ]
}
```

`--detected` is optional; when supplied, each `object_id` is checked against the
detector output (an unknown id is rejected).

## Guarantees / limitations

- No detector tuning, no RTM/truth/tolerance changes — this only records and
  aggregates human judgement.
- A real PDF is never treated as golden truth, and user PDFs are not committed.
- Not a web editor yet; corrections are recommendations, not auto-applied.
