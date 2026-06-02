# [D3 RTM frozen promotion report]

Scope: handoff T3 / D3 only — reproducible promotion of human-kept gallery
cases into a separate frozen fixture set. No detector / compare / overlay /
pytest-3 work.

## 1. Summary
- selected cases: index.md-driven (case-insensitive `keep`); CLI `--keep` override supported. Demo run via override selected 3: `core_fixed_header_footer`, `core_figure_caption_bottom`, `exp_table_4part_cont`.
- dropped/ignored cases: everything not kept (drop / blank / other). Demo: 39 of 42.
- output path: `picker_cmc_v1/tests/fixtures/rtm_frozen/`

## 2. Files changed
- `rtm_factory/promote.py`        NEW — promotion logic (parse index.md, select, copy, frozen MANIFEST/index)
- `promote_keep_cases.py`         NEW — thin CLI (--gallery/--out/--keep/--force/--allow-empty)
- `tests/test_rtm_promote_d3.py`  NEW — D3 focused validation (not the D6 trio)
- `.gitignore`                    +`rtm_frozen/` (demo / awaiting real Gate-B review; regenerable)
- Unchanged: generate.py, coverage.py, scenario_specs.py, self_check.py, builders/*, detector (none exists)

## 3. Commands run
- `python -m pytest tests/test_rtm_promote_d3.py -q` → 5 passed
- `python promote_keep_cases.py --gallery ../rtm_gallery --out ../rtm_frozen` → fail-safe: "no cases marked keep" (real index.md has empty review columns)
- `python promote_keep_cases.py --gallery ../rtm_gallery --out ../rtm_frozen --keep core_fixed_header_footer,core_figure_caption_bottom,exp_table_4part_cont` → promoted 3 (dropped 39, source=cli)
- re-run without `--force` → fail "output dir already exists" (exit 1); with `--force` → regenerates

## 4. Promotion behavior
- index.md keep/drop parsing: reads the `keep/drop` column (5th) of the gallery review table; only `keep` (case-insensitive: keep/KEEP/Keep) is promoted; drop/blank/other ignored. Header & `|---|` separator rows skipped. `--keep a,b` overrides index.md (selection_source becomes `cli`); unknown ids raise.
- output overwrite policy: copy-only (gallery never mutated). If output dir exists → fail by default; only `--force` deletes & regenerates. Frozen cases are never auto-deleted otherwise.
- allow-empty behavior: 0 keep → fail by default; `--allow-empty` permits an empty frozen set (testing only).

## 5. Validation result
- pass/fail: PASS
- tests run: `tests/test_rtm_promote_d3.py` — 5 passed:
  1. index.md parsing skips header/separator
  2. keep-only selection (keep2/drop1/blank1 → frozen has exactly the 2 keep; gallery untouched; MANIFEST selected_count=2 dropped_count=2)
  3. existing output fails without `--force`, regenerates with `--force`
  4. empty selection fails unless `--allow-empty`
  5. CLI `--keep` override (+ unknown id rejected)

## 6. Generated artifacts (demo via --keep)
- rtm_frozen MANIFEST: `rtm_frozen/MANIFEST.json`
  - schema_version="rtm-frozen-v0", source_gallery_schema_version="rtm-gallery-v0", coordinate_unit=pdf_pt, coordinate_origin=top-left
  - promotion={source_gallery:"../rtm_gallery", selection_source:"cli", selected_count:3, dropped_count:39}
  - cases: original gallery entries preserved (relative paths valid under frozen)
- rtm_frozen index: `rtm_frozen/index.md` (frozen list, not a review form)
- sample promoted cases: `core_fixed_header_footer` (3 pages → p01–p03 PNG copied), `exp_table_4part_cont` (4 pages → p01–p04 copied), `core_figure_caption_bottom`. Each dir carries pdf + truth.json + notes.md + all PNGs.

## 7. Did not touch
- detector code: not touched (no detector module exists in tree)
- compare harness: not started (D4)
- overlay/diff: not started (D5)
- pytest-3 full suite: not built (D6) — D3 test is a separate file `test_rtm_promote_d3.py`, not `test_rtm_frozen_fixtures.py`

## 8. Known limitations
- The committed real `rtm_frozen` set is empty until a human fills the `keep/drop` column in `rtm_gallery/index.md` (Gate B). The demo frozen set was produced with `--keep` override and is gitignored, not human-approved.
- promotion success != detector pass — no detector correctness is claimed.
- Deferred (your note, before D4): `get_text("dict")` truth-region overlap check in self_check; not part of D3.

Stopping after D3 as instructed. Awaiting accept/reject before D4 (`compare_detector_to_truth.py`).
