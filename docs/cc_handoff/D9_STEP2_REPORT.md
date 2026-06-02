# [D9 step2 report] figure/table sequence cases + title-gap + layout-consistency gates

Builds on step1 (target-aware filler, contamination 97→0). Adds the curated
multi-target sequences the picker must disambiguate, with truth that records
ordering and interstitial (non-target) text, and strict consistency gates.

## 1. Summary
- case count: 50 → **69** (cap raised 50→80 per your D9: soft 65–75, hard 80)
- new cases: 19 = 10 sequences + 6 title/gap combos + 3 header/footer-combined
- non_target↔target overlap: **0** across all 69 (audit CSV attached)
- target↔target overlap: 0 ; text-overlap 154/154 ; self_check PASS ; pytest 45 passed

## 2. Files changed (patch attached: D9_step2.patch, commit 21cd8ad)
- `rtm_factory/sequence.py` NEW — SequenceBuilder (band-based vertical stacker)
- `scenario_specs.py` — 19 new cases via SequenceBuilder
- `models/truth/builders` — TableSpec.caption_position; FigureTruth/TableTruth record `title_position`+`title_body_gap_lines`; NonTargetTruth carries `role`/`line_count`/`between`; case truth carries `layout_sequence`
- `render.py` — draws controlled interstitial text (non-target) + target-aware filler avoids it
- `templates.py` — 2-line header, ruled 2-line footer
- `self_check.py` — cap→80 + NEW layout-consistency gates
- `tests/test_rtm_full_integration_d6.py` — gate cap→80

## 3. Required sequence cases (all present)
figure-figure, figure-1line-text-figure, figure-2line-text-figure, figure-table,
table-figure, table-table, table-1line-text-figure, table-2line-text-figure,
figure-1line-text-table, figure-2line-text-table. (full list: sequence_cases.md)

## 4. Truth augmentation (as requested)
- `layout_sequence`: e.g. `[{"type":"figure","id":"3-5"},{"type":"non_target_text","line_count":1},{"type":"figure","id":"3-6"}]`
- non_target metadata: `{"kind":"non_target_text","bbox":[...],"role":"interstitial_text","line_count":1,"between":["figure:3-5","figure:3-6"]}`
- per target: `"title_position":"above|below"`, `"title_body_gap_lines":N`
- generic body bands recorded as `role":"body_filler"`

## 5. Title / gap combos
figure & table, title above & below, title-body gap 0 / 1 / 2 lines — present
across the 6 `exp_gap_*` cases plus the sequence cases (figure below g1, table above g1).

## 6. Header/footer-combined
- `exp_hfseq_2line_header_fig_fig` — 2-line running header (chapter / subsection) over figure-figure
- `exp_hfseq_footerbar_fig_table` — figure-table over a ruled 2-line footer bar
- `exp_hfseq_jitter_table_t1_fig` — table-text-figure with jittered header+footer

## 7. self_check gates added (strict; intentional_overlap_stress exempt)
1. generic body text ↔ target overlap (step1)
2. target ↔ target unintended caption/body overlap
3. layout_sequence order vs actual y order
4. interstitial line_count vs band height (1 line = 12pt)
5. title_position above/below vs actual caption/body y
6. title_body_gap_lines vs actual y-gap
Negative proof: a crafted bad truth triggers all 5 violation classes (8 errors).

## 8. Validation
- `python generate.py` → 69 cases, text-overlap 154/154, self_check PASS
- `python -m pytest tests -q` → 45 passed; `-m "not slow"` / `-m rtm_integration` green
- overlap_audit.csv → every case non_target_target=0, target_target=0

## 9. Attached visual artifacts
- D9_STEP2_REPORT.md, D9_step2.patch, MANIFEST.json, SELF_CHECK_REPORT.json
- sequence_cases.md, overlap_audit.csv
- samples/ (6 PNGs: fig-fig, fig-1line-text-fig, fig-2line-text-table, table-fig, table-table, 2line-header fig-fig)
- sequence_contact_sheet.jpg
- full rtm_gallery tar (separate attachment)

## 10. Did not touch
detector code · compare tolerance · CLI features · rtm_frozen durable (still empty; gallery NOT promoted) · Gate B.

Commit `21cd8ad` on `picker-cmc-d03`. Requesting review of the sequence layout
realism + truth schema (layout_sequence / non-target metadata / title-gap), and
go-ahead for any remaining D9 step (or closeout).
