# [D9 step3 report] required coverage for sequence/title-gap + self_check gate summary

Closes the three cleanups you required before D9 closeout. No new layout
concepts — only coverage enforcement, the missing title/gap cross-product, and
gate-result reporting.

## 1. Summary
- case count: 69 → **73** (within 70–80; hard cap 80 held)
- coverage_summary: **missing=[] below_min=[]** with the new axes now REQUIRED
- all D9 self_check gates: **0 failures**, now reported per-gate in SELF_CHECK_REPORT.json
- pytest 45 passed; generic_text_target_overlaps=0; target_target_unintended_overlaps=0

## 2. Cleanup 1 — required coverage axes (not just counts)
Added to `AXIS_REQUIREMENTS`, derived structurally in `coverage.py`:
- `seq`: 10 patterns, **1-line vs 2-line kept distinct** (`figure_text1_figure` ≠ `figure_text2_figure`). Old merged `seq:figure_text_figure` coverage_hints removed.
- `interstitial_text.lines`: none / one_line / two_line
- `title_gap`: figure&table × above/below × gap 0/1/2 (12 values)
- `sequence.with_common_regions`: no_common / two_line_header / footer_bar_two_lines / jittered_common

Counts (coverage_new_axes.md attached):
```
seq: every one of the 10 present (>=1)
interstitial_text.lines: none=66 one_line=4 two_line=3
title_gap: all 12 present — figure_above_g0=1 g1=3 g2=1, figure_below_g0=1 g1=19 g2=1,
           table_above_g0=1 g1=22 g2=1, table_below_g0=1 g1=1 g2=1
sequence.with_common_regions: no_common=10 two_line_header=1 footer_bar_two_lines=1 jittered_common=1
```
Negative proof: dropping the figure_table sequence cases moves `seq:figure_table`
into `coverage_summary.missing` → the gate now fails (it is enforced, not incidental).

## 3. Cleanup 2 — title/gap full cross-product
Added the 4 previously-unproven combos as dedicated cases:
`exp_gap_fig_above_g1`, `exp_gap_fig_below_g2`, `exp_gap_tbl_above_g2`, `exp_gap_tbl_below_g1`.
All 12 title_gap values are now present (table above).

## 4. Cleanup 3 — SELF_CHECK_REPORT gate summary
`SELF_CHECK_REPORT.json.d9_gates`:
```json
{
  "generic_text_target_overlaps": 0,
  "target_target_unintended_overlaps": 0,
  "sequence_order_failures": 0,
  "interstitial_line_count_failures": 0,
  "title_position_failures": 0,
  "title_gap_failures": 0,
  "checked": {"targets": 75, "interstitials": 7, "sequences": 23}
}
```
So each gate shows how many were checked and how many failed — not just "no error → pass".

## 5. Validation (pass criteria)
- total cases 73 (70–80) ✓
- coverage_summary missing=[] below_min=[] ✓
- required coverage includes sequence/title-gap/interstitial/common-region-combo ✓
- all D9 gate summary = 0 failures ✓
- generic_text_target_overlaps = 0 ✓ ; target_target_unintended_overlaps = 0 ✓
- `python -m pytest tests -q` → 45 passed ; `-m "not slow"` / `-m rtm_integration` green ✓
- detector / compare tolerance / CLI / rtm_frozen durable untouched ✓

## 6. Attached artifacts
- D9_STEP3_REPORT.md, D9_step3.patch (commit 6463f53), MANIFEST.json, SELF_CHECK_REPORT.json
- coverage_new_axes.md (the 4 new axes' counts), sequence_cases.md (23 cases), overlap_audit.csv (all 0)
- samples/ (8 PNGs: 4 sequence + 4 title-gap matrix), sequence_titlegap_contact_sheet.jpg
- full rtm_gallery tar available on disk (docs/cc_handoff/D9_step3_gallery.tar.gz) — say the word and I attach it

## 7. Did not touch
detector code · compare tolerance · CLI features · rtm_frozen durable (still empty; NOT promoted) · Gate B · unrelated refactor.

Commits: 6f2378e (step1) → 21cd8ad (step2) → 6463f53 (step3) on `picker-cmc-d03`.
Requesting D9 closeout (or any remaining cleanup).
