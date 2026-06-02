# [D7 RTM common-region realism expansion report]

Scope: handoff D7 — slow-marker cleanup + header/footer/watermark structural
diversity and deterministic per-page jitter, with new coverage axes. NOT a
detector; no detector wiring, no tolerance/truth-schema change, no YAML feature
expansion, no Gate-B.

## 1. Summary
- total cases (before): 42
- new cases: 8
- final case count: 50 (D6 gate's 30–50 range held; not exceeded)
- slow marker cleanup: done — full-gallery tests are now all `@slow`; `-m "not slow"` no longer builds the full gallery (runs in <1s)

## 2. Files changed
- `rtm_factory/models.py`             HeaderFooterSpec += kind/jitter_x/jitter_y/rule_jitter_y/first_page_suppressed; WatermarkSpec += jitter_pos/jitter_rot/jitter_opacity/near_footer; CaseSpec += extra_regions (truth schema unchanged)
- `rtm_factory/layout.py`             page_jitter()/jittered_bbox() — deterministic per-page offset (coprime multipliers so it actually varies)
- `rtm_factory/templates.py`          + subtitle_only/doc_title headers, page_only/page_x_of_y/distribution_notice footers, render_template gains total `pages`
- `rtm_factory/builders/header_footer.py`  first-page suppression, per-page xy + rule-y jitter, total-pages
- `rtm_factory/builders/watermark.py`      per-page position/rotation/opacity jitter; truth records actual rotation
- `rtm_factory/render.py`             draws extra_regions; passes page_count
- `rtm_factory/scenario_specs.py`     +8 D7 cases
- `rtm_factory/coverage.py`           +6 axes (hf.rule/page_number_position/subtitle_position/support/jitter, wm.jitter) + derivation + min1 exceptions
- tests: `test_rtm_full_integration_d6.py` (module @slow), `test_rtm_factory_generation.py` (@slow), `test_rtm_cli_d55.py` (2 gallery tests @slow)
- `.gitignore`                        +D7 handoff tarball

## 3. Commands run
- `python generate.py` → "generated 50 RTM candidate cases … text-overlap 118/118 matched, 8 skipped"
- `python -m pytest tests -q` → 45 passed
- `python -m pytest tests -q -m "not slow"` → 32 passed (no full-gallery build)
- `python -m pytest tests -q -m rtm_integration` → 8 passed; no PytestUnknownMarkWarning
- CLI subprocess gate (test_rtm_cli_subprocess_d6) exercises `rtm_cli.py generate/list-scenarios/self-check/compare/overlay --json`

## 4. New layout patterns
- header/footer rule/bar: header_rule, footer_rule, both_rules (rules driven by rule_line on header/footer/extras)
- page number positions: bottom_center (existing), bottom_right (multi-part right segment), page_x_of_y ("Page x of y")
- subtitle positions: centered (existing subtitle headers), top_right (new)
- multi-part footer: left document title + center distribution notice + right page number (footer + 2 extra_regions)
- first-page suppression: running header hidden on page 1, present on pages 2+
- jitter: deterministic per-page header xy jitter (±3/±2), even/odd mirror + jitter, rule-y jitter; truth stores the ACTUAL per-page bbox (verified: page-to-page bboxes differ)
- watermark jitter: variable license text + position jitter; near-footer watermark with rotation/opacity jitter (truth stores actual rotation)

## 5. Coverage update
- new coverage axes: hf.rule, hf.page_number_position, hf.subtitle_position, hf.support, hf.jitter, wm.jitter (derived structurally from the new spec fields; positions via coverage_hints where not structural)
- min1/min2 exceptions: the 14 D7 stress values (header_rule/footer_rule/both_rules, bottom_right/page_x_of_y, top_right, first_page_suppressed, xy_jitter/rule_y_jitter/evenodd_jitter, wm position/rotation_opacity/variable_text/near_footer) are min1 with justification in MANIFEST.coverage_summary.exceptions; their "none"/common counterparts stay min2.
- coverage_summary result: total 50, missing=[], below_min=[]. Sample counts — hf.rule {none:37, header_rule:5, footer_rule:4, both_rules:4}; hf.jitter {none:48, xy_jitter:1, rule_y_jitter:1, evenodd_jitter:1}; wm.jitter {none:48, position_jitter:1, rotation_opacity_jitter:1, variable_text_jitter:1, near_footer:1}; hf.support {all_pages:13, first_page_suppressed:1, partial_support:2}.

## 6. Self-check / pytest result
- generate: 50 cases, self_check PASS
- self_check: coverage gate (missing/below_min empty) + text-overlap gate 118/118 matched, 8 skipped (rotated/morph watermarks, reasons recorded) — importantly the overlap check uses each page's ACTUAL (jittered) bbox, so jitter cases pass without assuming fixed bboxes
- pytest: 45 passed; `-m "not slow"` 32 passed; `-m rtm_integration` 8 passed
- markers: slow + rtm_integration registered in pytest.ini; no warnings

## 7. Did not touch
- detector code: not touched (none exists)
- compare tolerance: unchanged
- truth schema: unchanged (jitter recorded as ordinary per-page common_regions bbox)
- rtm_frozen durable: none committed (only rtm_frozen_demo/, gitignored)
- detector integration: not started

## 8. Known limitations
- Jitter is deterministic (page-indexed), not random — reproducible by design; statistical/group bbox is explicitly out of scope (detector may derive it later; RTM truth/compare/overlay stay per-page).
- Multi-part footer is modeled as 3 footer common_regions on a page; matched by (page, kind, ordinal) in compare, which is order-stable for the generator.
- "thick_bar_or_double_rule" from the suggested axis list was not generated (kept out of requirements to avoid a 0-count required value); can be added later if needed.

Stopping after D7 as instructed. Awaiting next direction (detector integration / human frozen Gate B remain held).
