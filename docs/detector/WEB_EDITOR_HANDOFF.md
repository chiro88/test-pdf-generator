# Web editor handoff

How the next product milestone (web editor / setup-YAML / save-manifest) should
consume the detector and review tooling. **The detector result is an editable
initial proposal, never a final answer.**

## Data the editor consumes

1. **`detector-output-v0` manifest** (`detected_manifest.json`) — the regions to
   render and edit. Contract: `DETECTOR_OUTPUT_V0_CONTRACT.md`. Coordinates are
   PDF points, top-left origin; render overlays directly (no axis flip).
2. **Review package** (from `run_detector_on_pdf.py`): `pages/*_overlay.png`,
   `crops/*_body.png`, `review_index.md`, `review_result.template.yaml`.
3. **Review feedback schema** (`real-pdf-review-v0`) — the editor's save format for
   human decisions/corrections (see below).

## Editing model

- Each figure/table object has a stable `object_id = "<figure|table>:<index>:page<N>"`.
- The editor presents `caption_region` / `body_region` / `context_region` as draggable
  boxes over the rendered page; the detector values are the **initial proposal**.
- An operator can: accept, adjust a region bbox, mark false_positive, add a missed
  object, fix title/index, or flag a common-region issue.

## Save format → review feedback

The editor should serialize operator actions into a `real-pdf-review-v0` document
(YAML or JSON), the same contract the CLI consumes:

```yaml
schema_version: real-pdf-review-v0
pdf: <name>.pdf
reviewer: <user>
objects:
  - object_id: figure:3-3:page1
    decision: accept            # or bad_body_region / false_positive / wrong_title / ...
    expected_change:            # optional operator-corrected bbox
      body_region: [x0, y0, x1, y1]
    notes: "..."
missed_objects:
  - { kind: table, page: 2, index: "3-2", approximate_region: [x0,y0,x1,y1] }
```

Then `summarize_review_feedback.py` (or its `detector.review_feedback.summarize`)
produces `review_summary.json` with per-issue counts and `recommended_next_tasks`.
`detector.review_feedback` already provides: `object_id_for`, `parse_object_id`,
`build_review_template`, `load_review`, `validate_review`, `summarize`.

## What the editor must NOT assume

- A real-PDF detection is **not** ground truth — always editable, always reviewed.
- Watermark handling for rotated/morph/image-like marks is a known limitation
  (region not PDF-derivable) — expose it as "needs manual placement".
- Semantic content (table cell meaning, signal semantics) is out of scope.

## Integration checklist

- [ ] Render `detected_manifest.json` regions over the PDF (PDF-pt, top-left).
- [ ] Make every region bbox editable; keep `object_id` stable across edits.
- [ ] Support add-missed-object and false-positive removal.
- [ ] Save edits as a `real-pdf-review-v0` document.
- [ ] Round-trip through `validate_review` before persisting.
- [ ] Never commit user PDFs or rendered artifacts (`pdf/`, `artifacts/` are ignored).

## Reference points

- Contract: `DETECTOR_OUTPUT_V0_CONTRACT.md`
- Review workflow: `REAL_PDF_REVIEW_WORKFLOW.md`
- Operator guide: `docs/review/REAL_PDF_OPERATOR_REVIEW.md`
- Regression gate before shipping detector changes: `DETECTOR_REGRESSION_COMMANDS.md`
