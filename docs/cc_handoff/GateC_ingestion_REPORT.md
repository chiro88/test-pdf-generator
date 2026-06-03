[Gate C feedback ingestion report]

Ingested GPT's Gate C visual review (all 10 objects = `bad_body_region`) into the
review schema and summarized it. No detector code changed; no RTM/truth/tolerance
changes.

## 1. Actions
- Filled `GATE_C_OBJECT_LIST.csv` `decision` column (+ appended `notes`) with the
  10 decisions from GPT's review.
- Wrote `dp_sample/review_result.yaml` and `dp_sample1/review_result.yaml` from the
  templates (decision + notes per object; reviewer = "GPT (Gate C visual review)").
- Ran `tools/summarize_review_feedback.py` per PDF, and produced a unified
  Gate C summary across both PDFs.

## 2. Commands run
- `python tools/summarize_review_feedback.py --review <pdf>/review_result.yaml
   --detected <pdf>/detected_manifest.json --out <pdf>/review_summary.json --json`
   (for dp_sample and dp_sample1)
- unified summary over the merged manifests → `GATE_C_review_summary.json`

## 3. Generated review_summary.json (unified)
```json
{
  "reviewed_objects": 10,
  "accepted": 0,
  "missed_objects": 0,
  "issues": {
    "bad_body_region": 10,
    "false_positive": 0,
    "missed_object": 0,
    "bad_caption_region": 0,
    "bad_context_region": 0,
    "wrong_title": 0,
    "wrong_index": 0,
    "common_region_issue": 0
  },
  "recommended_next_tasks": [
    "Improve body_region inference for flagged figures/tables (e.g. waveform lower-bound)."
  ]
}
```
Matches the expected Gate C result (reviewed 10 / accepted 0 / bad_body_region 10 /
missed 0 / false_positive 0). Per-PDF: dp_sample 6/6, dp_sample1 4/4.

## 4. Finding
- real-PDF **anchor detection is usable** (titles/indices correct, 0 false positives,
  0 missed in this pass).
- real-PDF **body_region inference is not yet usable** for tables and
  waveform/diagram figures — crops capture only a caption/header strip, one
  sub-block, or a narrow frame fragment instead of the full body.

## 5. Did not touch
- detector algorithm: unchanged
- rtm_frozen / truth schema / compare tolerance / RTM scenarios: unchanged
- real PDF / rendered artifacts: not committed (only this report)

## 6. Next milestone
- **D20: real-PDF body_region inference for unenclosed diagrams/tables** — focus on
  waveform/diagram line clusters and table row extents. (Coding milestone; not
  started in this ingestion step.)

Stopping after the Gate C ingestion report per instruction.
