# [D5.5 RTM CLI usability layer report]

Scope: handoff D5.5 — wrap the RTM factory in one LLM/agent-friendly CLI with
machine-readable `--json`, stable exit codes, structured error_codes, and
scenario/template discovery. No detector, no D6 full gate, no scenario/tolerance/
truth-schema changes.

## 1. Summary
- CLI entrypoint: `rtm_cli.py` (thin) → `rtm_factory/cli.py` (dispatch/handlers)
- commands implemented: generate, generate-case, list-scenarios, list-templates, validate-scenario, self-check, promote, compare, overlay (9 subcommands; generate-case covers both named-scenario and scenario-file)
- --json support: every command; with `--json`, stdout is exactly one JSON object (warnings → stderr only)

## 2. Files changed
- `rtm_factory/errors.py`       NEW — RtmError + error_code→exit-code map
- `rtm_factory/scenario_io.py`  NEW — list_scenarios/list_templates, load_scenario_file (YAML+JSON), scenario_to_casespec validation
- `rtm_factory/cli.py`          NEW — generate_gallery + 9 command handlers + argparse + JSON/exit handling
- `rtm_cli.py`                  NEW — thin entrypoint
- `tests/test_rtm_cli_d55.py`   NEW — 11 tests
- `.gitignore`                  +D5_5 handoff tarball
- truth schema / models.py / detector / compare tolerances unchanged

## 3. Commands run
- `python -m pytest tests/test_rtm_cli_d55.py -q` → 11 passed; full `tests/` → 37 passed
- in-process smoke (via cli.main): list-scenarios/list-templates/generate/generate-case/validate-scenario/self-check/compare/overlay all return well-formed JSON; invalid input returns pure JSON error

## 4. CLI contract
- generate: `--out --seed --force --json` → builds full 42-case gallery + self-check; returns gallery/manifest/index/case_count/text_overlap. Existing out without --force → OUTPUT_DIR_EXISTS.
- generate-case: `--case-id <built-in> | --scenario-file <yaml/json> --out --force --json` → one PDF + truth + PNG(s) + notes; returns their paths.
- list-scenarios: `--json` → built-in scenario ids + axes + notes.
- list-templates: `--json` → header/footer/watermark/table_caption/figure_alias/figure_body/caption_position/page_size/orientation/columns.
- validate-scenario: `<file> --json` → ok/valid + counts, or structured error.
- self-check: `--gallery --json` → coverage {total,missing,below_min} + text_overlap {checked,passed,skipped,failures}.
- promote: `--gallery --out --keep --force --allow-empty --json` → wraps promote.py.
- compare: `--truth-root --detected --out --tolerance-profile --allow-extra --json` → wraps D4; passed bool + summary + report paths.
- overlay: `--truth-root --detected --compare-report --out --case-id --failures-only --all --pages --scale --json` → wraps D5; manifest/index/pages_rendered.

## 5. JSON output / error behavior
- success schema: `{"ok": true, "command": "...", ...payload}`
- error schema: `{"ok": false, "error_code": "...", "message": "...", "field"?: "...", "allowed_values"?: [...]}`
  e.g. unknown figure body → `error_code=SCENARIO_UNKNOWN_TEMPLATE, field="figures[0].body_template", allowed_values=["waveform","diagram","raster","mixed"]`
- error codes: SCENARIO_FILE_NOT_FOUND/UNREADABLE, SCENARIO_INVALID_VALUE, SCENARIO_UNKNOWN_TEMPLATE, SCENARIO_BAD_BBOX, SCENARIO_OUT_OF_PAGE_BOUNDS, SCENARIO_UNSUPPORTED_PAGE_SIZE, OUTPUT_DIR_EXISTS, INVALID_INPUT, SELF_CHECK_FAILED, PROMOTION_FAILED, COMPARE_FAILED, PDF_GENERATION_FAILED, OVERLAY_FAILED
- exit codes: 0 success · 1 validation/comparison failed (e.g. compare passed=false, self-check/promote failed) · 2 invalid input/schema/unreadable · 3 internal generation/rendering failure
- with `--json`, even errors print ONLY the JSON object to stdout (verified by test).
- D5 follow-up: overlay `--pages` with non-integer input now returns INVALID_INPUT instead of a raw ValueError.

## 6. Validation result
- tests: `tests/test_rtm_cli_d55.py` 11 passed —
  list-scenarios, list-templates, generate, generate-case, validate-scenario(ok), validate-scenario(unknown template → SCENARIO_UNKNOWN_TEMPLATE+field+allowed_values), validate-scenario(out-of-bounds → SCENARIO_OUT_OF_PAGE_BOUNDS), self-check(coverage+overlap), compare(pass preserved), overlay(manifest/index), invalid input emits pure JSON.
- sample success JSON (generate-case): `{"ok":true,"command":"generate-case","case_id":"core_figure_caption_bottom","output_dir":"...","pdf":"...","truth":"...","previews":["...p01.png"],"notes":"...","page_count":1}`
- sample error JSON (bad template): `{"ok":false,"error_code":"SCENARIO_UNKNOWN_TEMPLATE","message":"...","field":"figures[0].body_template","allowed_values":["waveform","diagram","raster","mixed"]}`

## 7. Did not touch
- detector code: not touched (none exists)
- D6 full pytest integration: not built
- rtm_frozen durable fixtures: none committed (only rtm_frozen_demo/, gitignored)
- truth schema: unchanged; compare tolerances unchanged; scenario set not expanded

## 8. Known limitations
- YAML supported via PyYAML (present); scenario files accept YAML or JSON (one parser). If PyYAML were absent, JSON would still parse but `.yaml` would error — acceptable for now.
- generate-case from scenario-file builds one case but does not run the gallery-level coverage gate (single-case scope); self-check remains the gallery gate.
- The legacy single-purpose scripts (generate.py, promote_keep_cases.py, compare_detector_to_truth.py, render_compare_artifacts.py) still work; rtm_cli.py is the unified front door for agents.

Stopping after D5.5 as instructed. Awaiting accept/reject before D6 (pytest full integration).
