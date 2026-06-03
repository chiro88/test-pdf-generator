# [D14 detector body/context inference report]

Scope: handoff D14 — figure/table `body_region` / `context_region` inference.
Still no-truth; common-region contract untouched.

## 1. Summary
- body/context changes: body = dominant frame rect (fixes x-overshoot), column-aware (no two-column bleed), context = union(caption, body)+margin clamped between sequence neighbours
- frozen cases run: 49 / 49 (0 crashes)
- detector-output-v0 validation: PASS (0 schema errors)

## 2. Files changed
- `detector/region_inference.py` (frames + column-aware infer + context clamp)
- `detector/pipeline.py` (frame inference + sequence-aware context bounds)
- `tests/test_detector_body_context_d14.py` (9) NEW
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / common-region contract: untouched

## 3. Commands run
- runner with the real detector over rtm_frozen 49
- `python -m pytest tests -q` → 108 passed

## 4. No-truth guarantee
- truth read by detector: **no**
- verification: `test_no_truth_guarantee` (detect with no truth.json beside the PDF); body is the frame rect from the PDF, columns from caption text x.

## 5. Metrics vs D13
| metric | D13 | D14 |
|---|---|---|
| objects matched | 96/100 | 96/100 (held ≥96) |
| missing | 4 | 4 |
| extra | 9 | 9 (≤9 held) |
| regions ok | 159/206 | **186/206** (≥175 target) |
| cases passed | 28/49 | **37/49** (≥34 target) |
| body_region failures | 12 | **0 (100% reduction)** |
| context_region failures | 14 | **3 (78% reduction)** |
| caption_region failures | 12 | 8 (bonus, follows body column) |
| anchors | 53/53 | 53/53 |
| table missing / extra | 0 / 0 | 0 / 0 |
| negative FP | 0 | 0 |

## 6. Sequence results (context does not eat a neighbour's body/caption)
- figure-figure: separate bodies/contexts (`exp_seq_fig_fig`).
- figure-text-figure: 1/2-line interstitial text excluded from both contexts (`exp_seq_fig_t1_fig`, `_t2_fig`).
- figure-text-table: figure context ends before the table caption (`exp_seq_fig_t2_table`).
- table-figure: table body/context do not invade the figure (`exp_seq_table_fig`).
- table-table: two table bodies separated (`exp_seq_table_table`).

## 7. X-range / column results
- two-column: figure bodies stay in-column — `[54,140,286,272]` / `[326,140,558,272]` (matches truth exactly, 0 bleed).
- page-wide: `core_wide_diagram_xrange` figure kept full width (frame rect preserved, not clamped to margins).
- table wide / figure wide: frame rect drives the width, so wide targets keep their span.

## 8. Artifacts
- detected manifest: `artifacts/detector_rtm/detected_manifest.json`
- compare report: `artifacts/detector_rtm/compare/compare_report.{json,md}`
- overlay path: `artifacts/detector_rtm/overlay/`
- sample overlay attached.

## 9. Did not touch
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / common-region contract: unchanged

## 10. Known limitations (remaining failures, next-iteration)
- caption y: 8 residual caption-band-height failures (truth cap_h 18–46 vs 5pt y-tol) — inherent to per-case truth band heights.
- common-region bbox: 9 header/footer/watermark band-height deltas + missing/extra footer (4 missing, 3 extra) — mostly multipart-footer narrow bands and footer band-height variance (D13 domain).
- watermark: 6 extra watermark (extractable text bbox vs truth watermark band, and detections where truth watermark is rotated) — extractable text detection is coarse.
- semantic waveform/diagram/table interpretation: out of scope; bodies are region bands, not interpreted content.

Commit `411ea98` on `picker-cmc-d03` (after D13 `215c22c`).
Requesting D14 acceptance and the next detector target.
