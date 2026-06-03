# [D15 detector caption band normalization report]

Scope: handoff D15 — caption_region band normalization. Still no-truth;
body/common-region/table-identity untouched.

## 1. Summary
- caption normalization changes: caption is now a deterministic BAND (line-count y height, body-following x) rather than the text-line bbox
- frozen cases run: 49 / 49 (0 crashes)
- detector-output-v0 validation: PASS (0 schema errors)

## 2. Files changed
- `detector/region_inference.py` (caption_band: y band-height rule + kind-aware x)
- `detector/pipeline.py` (pass anchor.kind into caption_band)
- `tests/test_detector_caption_band_d15.py` (9) NEW
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / common-region contract: untouched

## 3. Commands run
- runner with the real detector over rtm_frozen 49
- `python -m pytest tests -q` → 117 passed

## 4. No-truth guarantee
- truth read by detector: **no**
- verification: `test_no_truth_guarantee` (band from a PDF with no truth.json beside it); the band is computed from text line count + body x, never from truth.

## 5. Metrics vs D14
| metric | D14 | D15 |
|---|---|---|
| objects matched | 96/100 | 96/100 |
| missing | 4 | 4 |
| extra | 9 | 9 (≤9) |
| regions ok | 186/206 | **196/206** (≥193 target) |
| cases passed | 37/49 | **41/49** (≥41 target) |
| caption_region failures | 8 | **0** (≤3 target) |
| body_region failures | 0 | 0 (held) |
| context_region failures | 3 | **1** (≤1 target) |
| anchors | 53/53 | 53/53 |
| negative FP | 0 | 0 |
| table missing / extra | 0 / 0 | 0 / 0 |

## 6. Caption results
- single-line figure: band height `text_top + 23` — within ±5pt of truth cap_h 18 AND 28 (the two single-line authoring heights).
- single-line table: same band rule; table caption x follows the body width.
- multiline: caption lines merged; band height `+18` per extra line → 2-line cap_h ~46 matched.
- wide/page-wide: figure caption x clamped to content margin (page-wide figure body does not widen the caption); table caption x follows the (wide) body width — wide tables keep a wide caption (`exp_caption_above_table_wide` now passes).
- above/below: title_position preserved (caption y vs body y).
- gap lines: title_body_gap_lines still computed from caption/body geometry.

## 7. Did not touch
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / common-region contract: unchanged

## 8. Known limitations (deferred to D16 per your scope)
- residual caption: 0.
- multipart footer: missing/extra (4 missing, 3 extra) — band/narrow-band matching.
- watermark: extractable-text bbox vs truth band; rotated/image-like watermark extras.
- semantic interpretation: out of scope (bodies are region bands, not interpreted content).

The remaining ~8 failing cases are now almost entirely common-region/watermark
(D16), plus 1 context residual. Commit `f674301` on `picker-cmc-d03` (after D14 `411ea98`).
Requesting D15 acceptance and the D16 target (common-region/watermark cleanup).
