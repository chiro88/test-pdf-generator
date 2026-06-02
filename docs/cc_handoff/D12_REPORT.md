# [D12 detector table identity + caption band report]

Scope: handoff D12 — table identity/continuation linking + caption band
normalization. Still no-truth; D12 green = clear improvement over D11, not 0 fail.

## 1. Summary
- table identity: canonical `table_group_id` from index + continuation linking + same-index distinctness
- caption band: caption_region expanded from text line → content-column band (+ multiline merge)
- frozen cases run: 49 / 49 (0 crashes)

## 2. Files changed
- `detector/table_identity.py` NEW (canonical_group_id + assign_table_groups)
- `detector/region_inference.py` (+ caption_band)
- `detector/pipeline.py` (cross-page anchors, multiline merge, group assignment, caption bands)
- `tests/test_detector_table_caption_d12.py` (8) NEW
- rtm_frozen / RTM truth schema / compare tolerance / RTM scenarios: untouched

## 3. Commands run
- `run_detector_on_rtm.py --detector-cmd "detect_pdf.py --pdf {pdf} --out {out}"` over rtm_frozen 49
- `python -m pytest tests -q` → 80 passed

## 4. No-truth guarantee
- truth read by detector: **no** (detect_pdf takes only the PDF; no `--truth`)
- verification: `test_no_truth_guarantee` (detect with no truth.json beside the PDF) + truth never imported in `detector/`.

## 5. Metrics vs D11
| metric | D11 | D12 |
|---|---|---|
| objects matched | 61/100 | **71/100** |
| missing | 39 | 29 |
| extra | 24 | 20 |
| regions ok | 31/117 | **78/147** |
| caption_region failures | 28 | **12 (57% reduction ≥ 50% target)** |
| table missing | 17 | 17 |
| table extra | 17 | 17 |
| cases passed | 5/49 | **10/49** |
| figure anchors | 28/28 | 28/28 |
| table anchors | 25/25 | 25/25 |
| negative false positives | 0 | 0 |

## 6. Table identity results
- continuation groups: multipage/same-page continuations now share one canonical group_id with reading-order part_index. Verified: `core_multipage_table_cont` → tbl_002_001 (parts 1,2,3; markers `(cont)`), `exp_table_3part_cont` → tbl_010_001 (1,2,3) — both match truth.
- part_index: increments by reading order; first part is_continuation=false, later parts true with marker preserved.
- same-index duplicate behavior: independent same-index tables get distinct ids (not merged) — `test_same_index_separate_tables_distinct_groups`.

## 7. Caption band results
- figure captions: caption_region x-range now spans the content column ([margin, w-margin]) instead of the ~150pt text run → caption x deltas mostly within tolerance.
- table captions: same band normalization applied.
- multiline captions: merged into one band (verified taller than a single line).

## 8. Artifacts
- detected manifest: `artifacts/detector_rtm/detected_manifest.json` (contract-valid, 0 schema errors)
- compare report: `artifacts/detector_rtm/compare/compare_report.{json,md}`
- overlay path: `artifacts/detector_rtm/overlay/` (failure pages with truth vs detector + deltas)

## 9. Did not touch
- rtm_frozen / truth schema / compare tolerance / RTM scenarios: unchanged

## 10. Known limitations + one blocker for the "≥80 matched" target
- **objects matched is capped at 71 (not ≥80) by a TRUTH-side naming inconsistency**, not detector capability: 17 table objects in the frozen truth use NON-canonical group ids — `tbl_seq_*` (sequence tables), `tbl_gap_13_1` (gap tables), `tbl_004_002_a/_b` (same-title) — none derivable from the caption index. A truth-blind canonical detector (per your D12 rule) cannot match them. The canonical tables it CAN derive (tbl_002_001/010_001/007_009/014_003/015_002) already match, including continuation linking.
  - To lift matched to ~84, the RTM scenarios' sequence/gap/same-title `table_group_id`s would need canonicalizing (`tbl_seq_5_1`→`tbl_005_001`, `tbl_gap_13_1`→`tbl_013_001`, …) + a frozen re-promote — which is a SCENARIO change, explicitly out of D12 scope. **Requesting your call:** authorize that factory canonicalization (D12.5 / factory-fix), or accept 71 as the D12 result given the frozen-truth constraint.
- caption y: truth caption-band height varies per case (cap_h 18–46) and can exceed the 5pt y-tolerance; the 57% caption-failure reduction is from x-band normalization + a tuned bottom padding. The residual y mismatches are inherent to per-case truth band heights.
- common regions: still the repeated-line hook (header/footer); watermark not detected.
- body/context inference: unchanged from D11 (rough drawing-cluster bands).

Commit `af5a813` on `picker-cmc-d03` (after D11 `aa682dc`).
Requesting D12 acceptance + a decision on the table_group_id canonicalization blocker.
