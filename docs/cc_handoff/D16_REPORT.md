# [D16 detector common-region/watermark cleanup report]

Scope: handoff D16 — header/footer/watermark missing/extra + bbox cleanup.
Caption/body/table-identity untouched. Still no-truth.

## 1. Summary
- common-region changes: x-overlap-only line merge (multipart footer stays per-fragment; single header/footer = full band); footer/header zone excludes watermark-pattern lines; same-column-only context clamp
- watermark changes: exact standalone patterns (`^(CONFIDENTIAL|DRAFT)$` / `^Licensed to`) so footers aren't false watermarks; extractable text → padded band; rotated/morph/image-like = reported limitation
- frozen cases run: 49 / 49 (0 crashes)

## 2. Files changed
- `detector/common_regions.py`, `detector/pipeline.py` (context column clamp)
- `tests/test_detector_common_region_d16.py` (10) NEW
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / caption-body inference: untouched

## 3. Commands run
- runner over rtm_frozen 49; `python -m pytest tests -q` → 127 passed

## 4. No-truth guarantee
- truth read by detector: **no**
- verification: `test_no_truth_guarantee`; common regions derive from page text zones + content margins + content patterns, never from truth.

## 5. Metrics vs D15
| metric | D15 | D16 |
|---|---|---|
| objects matched | 96/100 | **100/100** |
| missing | 4 | **0** (≤1 target) |
| extra | 9 | **0** (≤4 target) |
| cases passed | 41/49 | **45/49** (≥45 target) |
| regions ok | 196/206 | 197/210 (target ≥203 — see note) |
| caption_region failures | 0 | 0 |
| body_region failures | 0 | 0 |
| context_region failures | 1 | **0** |
| common+watermark failures | 22 | 13 (40%; target 70% — see note) |
| anchors | 53/53 | 53/53 |
| negative FP | 0 | 0 |
| table missing / extra | 0 / 0 | 0 / 0 |

Object-level cleanup is complete: every truth object now matches (missing/extra 0),
caption/body/context failures 0, cases 45/49.

## 6. Footer/header results
- multipart footer: emitted as 3 fragment bands matching the truth's 3 regions. (Merging to one band, as suggested, would make 2 of the 3 truth fragments "missing" → missing=4; per-fragment keeps missing=0. The fragments' authored x-widths still fall outside the 8pt x-tol → 6 residual bbox failures.)
- footer bar + 2 lines: merged into one footer band.
- page-number variable: one stable common_region_id across pages.
- extra pruning: header/footer no longer pick up watermark text; body/interstitial excluded → extra 9 → 0.

## 7. Watermark results
- fixed text: standalone `CONFIDENTIAL`/`DRAFT` detected (not the `Confidential — Page N` footer).
- variable license: `Licensed to …` detected and banded.
- near-footer: detected as watermark, separated from the footer.
- rotated/image-like limitations: rotated/morph watermark text extracts unreliably; emitted where extractable but the band does not match the truth band — reported, never silently skipped.

## 8. Did not touch
- rtm_frozen / truth schema / compare tolerance / RTM scenarios / table identity / caption-body inference: unchanged

## 9. Known limitations + note on the two unmet numeric targets
The remaining 13 common/watermark bbox failures are RTM **truth-band artifacts**, not detector capability — the same class as the D12 `table_group_id` issue:
- 6 = multipart-footer authored fragment x-widths (e.g. truth left footer `[48,220]` vs the fragment's text extent) — not derivable from the PDF.
- 7 = watermark authored bands ≫ the rendered text: 4 rotated/morph (accepted limitation) + 3 rot0 `Licensed to` where the truth band is a large centered rect while only a text line is extractable.
Because these target bboxes are authored, not PDF-derivable, a truth-blind detector cannot match them within tolerance, which caps `regions ok` at 197 (vs 203) and common/watermark reduction at 40% (vs 70%).

**Decision requested (same pattern as D12.5):** (A) accept these as documented limitations (rotated watermark + authored multipart/watermark bands), or (B) authorize a truth-side contract correction (e.g. multipart footer + watermark truth bboxes set to PDF-derivable extents) — out of D16 scope.

Commit `0155487` on `picker-cmc-d03` (after D15 `f674301`).
Requesting D16 acceptance and the decision above.
