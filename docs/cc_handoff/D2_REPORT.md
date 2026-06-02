# [D2 RTM scenario expansion report]

Scope: handoff T1 + part of T2 (scenario expansion + coverage-gating self-check).
Detector / frozen-promotion / compare / overlay / pytest-3 were NOT started.

## 1. Summary
- total cases: 42  (range 30–50 ✓)
- core: 8
- negative: 6  (was 5; added `neg_false_table_reference` for the Table-reference-only axis)
- expanded: 28  (was 6)

## 2. Files changed (vs v0 baseline tarball)
- `rtm_factory/coverage.py`           NEW — axis taxonomy + structural tag derivation + summary
- `rtm_factory/models.py`             +1 field `CaseSpec.coverage_hints` (truth schema unchanged)
- `rtm_factory/scenario_specs.py`     rewrite of expanded set + helpers (`_figure/_table/_continuation`); core 8 kept verbatim
- `rtm_factory/self_check.py`         coverage gate + exact-name presence + diagonal-wm + A.1 + suffix checks
- `rtm_factory/gallery.py`            MANIFEST now carries `coverage_summary`
- `generate.py`                       writes per-case `coverage_tags` + top-level coverage summary
- Unchanged: builders/*, layout.py, templates.py, truth.py, render.py
- Full unified diff: `D2.diff` (796 lines) in the delivered tar.

## 3. Commands run
- `python picker_cmc_v1/tests/fixtures/rtm_factory/generate.py`  → `generated 42 RTM candidate cases`
- negative test (drop expanded set) → coverage gate reports 45 under-covered tags (gate is not a rubber stamp)

## 4. Self-check result
- pass/fail: PASS
- coverage summary path: `rtm_gallery/MANIFEST.json` → `coverage_summary` (counts / required / missing / below_min / exceptions)
- manifest path: `rtm_gallery/MANIFEST.json`
- index path: `rtm_gallery/index.md`  (all 42 cases; empty realism/keep-drop/critique columns)
- missing: []   below_min: []

## 5. Axis coverage highlights (case counts)
- page:    size letter×40 a4×2 · orient portrait×40 landscape×2 · cols single×40 two×2 · pages 1×26 3×9 2×4 8×2 4×1 · offset zero/nonzero both ≥3
- header/footer: none×32 header_only×4 footer_only×3 both×3 · mirrored×3 · partial_support×2 · variable page_number & subtitle ≥2 · rule_line many
- watermark: none×35 fixed×5 variable×2 · center×4 corner×3 · light×5 strong×2 · rot0×4 diagonal×3 · image_like×2
- figure:  caption above×2 below×many · alias Figure/Fig./FIGURE ≥2 · index dotted×3 integer×2 dashed×3 alpha×3 · title one_line/multiline ≥2 · body waveform×3 diagram×3 raster×3 mixed×2 · width column/page_wide ≥2 · multiple_per_page×2
- table:   single_page/continuation ≥2 · parts 2×5 3×2 4×1 · suffix (cont)×4 (continued)/continued/Continued/cont. ×1 each · same_title/different_title ≥2 · same_page_fragment×1 · normal/wide ≥2 · caption above many
- negative: plain_text / figure_of_merit / see_table_above / figure_ref_only / table_ref_only / weak_partial_header — each present by exact name

## 6. Generated artifacts
- rtm_gallery path: `picker_cmc_v1/tests/fixtures/rtm_gallery/`  (42 dirs · 42 PDF · 42 truth.json · 42 notes.md · 81 PNG)
- sample case ids: `core_figure_caption_top`, `exp_8page_mirror_hf`, `exp_table_4part_cont`, `exp_figure_multi_raster_multiline`, `exp_watermark_strong_diagonal_corner`

## 7. Known limitations / coverage exceptions (declared in MANIFEST `exceptions`)
- `tbl.parts:4` — 4-part continuation is a rare worst case; single instance.
- `tbl.suffix:(continued|continued|Continued|cont.)` — presence-only markers (handoff T2.7), one each.
- `tbl.fragment:same_page_fragment` — rare same-page split; single instance.
- `neg.kind:*` — named negative scenarios, presence-only by exact name.
- T2 item 1 (truth regions vs `get_text("dict")` bbox overlap) intentionally deferred — outside the D2 scope you set (T2 partial); ready to add when you greenlight.

## 8. Did not touch
- detector code: no  (no detector module exists in this tree; none created/edited)
- frozen promotion: no
- detector-vs-truth comparison: no
- overlay/diff: no
- pytest 3-suite: no

Stopping after D2 as instructed. Awaiting accept/reject before D3 (`promote_keep_cases.py`).
