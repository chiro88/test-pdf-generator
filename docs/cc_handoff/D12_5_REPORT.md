# [D12.5 RTM table identity contract correction report]

Scope: handoff D12.5 — RTM table identity contract correction (canonical,
PDF-derivable `table_group_id`) + detector `continued_from` output fix. The
detector was NOT tuned to guess RTM-internal ids; the TRUTH contract was fixed.

## 1. Summary
- frozen case count: 49 (unchanged)
- canonicalized table ids: sequence + gap + same-title truth ids are now canonical (PDF-derivable from the caption index)
- detector continued_from fix: continuation parts now emit `continued_from = table_group_id`

## 2. Files changed
- RTM factory: `rtm_factory/sequence.py` (canonical_table_group_id + SequenceBuilder.table derives it), `scenario_specs.py` (core_same_title occurrence ids)
- rtm_frozen: regenerated + re-promoted with the SAME 49 keep set — only 15 `truth.json` `table_group_id` fields changed; 0 PDF changes (layout byte-restored/unchanged); MANIFEST count 49
- detector/writer/validator: `detector/pipeline.py` emits `continued_from`; writer/validator already supported it (no contract change)

## 3. Commands run
- `python generate.py` → 73 cases, self_check PASS; re-applied the Gate B keep CSV to index.md
- `python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --force --json` → selected 49 / dropped 24
- runner with the real detector over rtm_frozen 49
- `python -m pytest tests -q` → 90 passed

## 4. Contract correction
- sequence table ids: `tbl_seq_5_1` → `tbl_005_001`, `tbl_seq_7_1/7_2` → `tbl_007_001/tbl_007_002`, … (canonical from index)
- gap table ids: `tbl_gap_13_1` → `tbl_013_001`
- same-title duplicate ids: `tbl_004_002_a/_b` → `tbl_004_002 / tbl_004_003` (occurrence rule)
- continuation continued_from: detector now sets `continued_from = group_id` for parts > 1 (matches truth `continued_from`); factory truth already canonical for continuation groups (tbl_002_001 / tbl_010_001 / tbl_015_002)

## 5. Metrics vs D12
| metric | D12 | D12.5 |
|---|---|---|
| objects matched | 71/100 | **88/100** (≥80 target MET) |
| missing | 29 | 12 |
| extra | 20 | 3 |
| table missing | 17 | **0** |
| table extra | 17 | **0** |
| continued_from field failures | (present) | **0** |
| regions ok | 78/147 | **127/198** |
| cases passed | 10/49 | **22/49** |
| caption_region failures | 12 | 12 (held) |
| anchors | 53/53 | 53/53 |
| negative false positives | 0 | 0 |

Table identity blocker is RESOLVED: matched ≥ 80, table missing/extra = 0.

## 6. No-truth guarantee
- truth read by detector: **no** (detect_pdf takes only the PDF; no `--truth`)
- verification: `test_no_truth_guarantee_still_holds` (detect with no truth.json beside the PDF) + the canonical id is derived from the PDF caption index, not from truth.

## 7. Did not touch
- compare tolerance: unchanged
- detector truth access: still none (no hardcoded tbl_seq_* aliases)
- scenario layout: unchanged (PDF/PNG byte-restored; only truth identity fields changed)
- case selection: unchanged (same 49 keep / 24 defer from Gate B)

## 8. Known limitations
- caption y: residual 12 caption failures from per-case truth caption-band height variance (cap_h 18–46 vs 5pt tolerance); unchanged from D12.
- common regions: still the repeated-line header/footer hook; watermark not detected → some common-region missing/extra.
- body/context: rough drawing-cluster bands (D11 heuristic; not the focus here).
- watermark: not detected.

Commit `e032fa4` on `picker-cmc-d03` (after D12 `af5a813`).
Requesting D12.5 acceptance and the next detector-improvement target (e.g. common-region bbox accuracy, body/context region inference).
