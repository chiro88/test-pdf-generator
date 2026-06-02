# [D13 detector common-region band normalization report]

Scope: handoff D13 — common-region (header/footer/watermark) band normalization.
Still no-truth; caption/body/context deliberately left as-is (D13 = common-region).

## 1. Summary
- common-region detector changes: header/footer emitted as content-margin BANDS (merged multiline, padded y) with stable common_region_id; extractable watermark text detection
- frozen cases run: 49 / 49 (0 crashes)
- detector-output-v0 validation: PASS (0 schema errors)

## 2. Files changed
- `detector/common_regions.py` (band normalization + watermark patterns + common_region_id)
- `detector_output/writer.py` (common_region accepts common_region_id)
- `detector/pipeline.py` (pass common_region_id)
- `tests/test_detector_common_region_d13.py` (9) NEW
- rtm_frozen / RTM truth schema / compare tolerance / RTM scenarios / table identity: untouched

## 3. Commands run
- runner with the real detector over rtm_frozen 49
- `python -m pytest tests -q` → 99 passed

## 4. No-truth guarantee
- truth read by detector: **no** (detect_pdf takes only the PDF)
- verification: `test_no_truth_guarantee` (header band detected from a PDF with no truth.json beside it); bands derive from page text + content margins, not truth.

## 5. Metrics vs D12.5
| metric | D12.5 | D13 |
|---|---|---|
| objects matched | 88/100 | **96/100** (≥92 target) |
| missing | 12 | 4 |
| extra | 3 | 9 |
| regions ok | 127/198 | **159/206** (≥145 target) |
| common-region failures | 33 | **9 (73% reduction, ≥50% target)** |
| watermark missing | 7 | **0** |
| cases passed | 22/49 | **28/49** |
| table missing / extra | 0 / 0 | **0 / 0** (held) |
| anchors | 53/53 | 53/53 |
| negative false positives | 0 | 0 |

## 6. Header/footer results
- 2-line header: merged into one band (x [48,564], height ~41) — `exp_hfseq_2line_header_fig_fig`.
- footer bar + 2 lines: merged into one footer band — `exp_hfseq_footerbar_fig_table`.
- page-number variable: digit-insensitive normalized text → one stable common_region_id across pages (`core_multipage_table_cont`).
- even/odd: per-page bands derived from each page's text → mirrored/offset handled, 0 crashes.
- jitter: per-page bands track the jittered position; one common_region_id retained.

## 7. Watermark results
- fixed text: detected by pattern (CONFIDENTIAL/DRAFT).
- variable text: `Licensed to <user>` detected (position-jitter case).
- near-footer: extractable near-footer watermark detected.
- rotated/image-like limitations: rotated/morph/image-like watermark text is unreliable from get_text and may be missed — reported here, never silently skipped; bbox of any extractable text is still emitted.

## 8. Artifacts
- detected manifest: `artifacts/detector_rtm/detected_manifest.json` (contract-valid)
- compare report: `artifacts/detector_rtm/compare/compare_report.{json,md}`
- overlay path: `artifacts/detector_rtm/overlay/`
- sample overlay attached.

## 9. Did not touch
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity: unchanged

## 10. Known limitations
- body/context: still the D11 drawing-cluster heuristic (not the D13 focus) — main remaining region failures.
- caption y: residual caption-band-height failures unchanged from D12 (truth cap_h variance vs 5pt tol).
- rotated/morph/image-like watermark: not reliably extractable; the 9 residual common-region failures + the `extra 9` are mostly multipart-footer narrow bands and watermark band-vs-text-span deltas.

Commit `215c22c` on `picker-cmc-d03` (after D12.5 `e032fa4`).
Requesting D13 acceptance and the next detector target (likely body/context region inference).
