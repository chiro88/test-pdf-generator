# [D10 detector-output-v0 integration scaffold report]

Scope: handoff D10 — the standard path `PDF → detector → detector-output-v0 →
compare → overlay` over the rtm_frozen golden set. NOT a detector algorithm.

    D10 green = detector integration path works
    D10 green ≠ detector correctness

## 1. Summary
- detector-output-v0 validator: `picker_cmc_v1/detector_output/validator.py` (structural contract only)
- runner: `picker_cmc_v1/tools/run_detector_on_rtm.py`
- compare/overlay linkage: runner reuses `rtm_factory.compare` + `rtm_factory.overlay` (no duplication, no contract change)

## 2. Files changed
- `picker_cmc_v1/detector_output/__init__.py` / `schema.py` / `validator.py` / `writer.py` NEW
- `picker_cmc_v1/tools/run_detector_on_rtm.py` NEW
- `tests/test_detector_output_schema_d10.py` (9) / `tests/test_rtm_detector_runner_d10.py` (5) NEW
- rtm_frozen / RTM truth schema / compare tolerance / scenarios: untouched

## 3. Commands run
- `python picker_cmc_v1/tools/run_detector_on_rtm.py --rtm-root .../rtm_frozen --out artifacts/detector_rtm --synthetic-from-truth --json`
  → `{"ok":true,"producer_mode":"synthetic-contract-test","case_count":49,"compare_passed":true}` exit 0
- detector unavailable (no `--detector-cmd`, no `--synthetic-from-truth`) → exit 2, `error_code=DETECTOR_UNAVAILABLE_OR_INVALID`
- `python -m pytest tests -q` → 59 passed; `-m "not slow"` 45; `-m rtm_integration` 9

## 4. Frozen input
- rtm_frozen case count: 49 (enumerated from MANIFEST.json)
- manifest path: `picker_cmc_v1/tests/fixtures/rtm_frozen/MANIFEST.json`

## 5. Output contract
- detected manifest (`detector-output-v0`): `{schema_version, coordinate_unit=pdf_pt, coordinate_origin=top-left, producer{name,version,mode}, cases[{case_id, pdf, pages[{page, common_regions, figures, tables}]}]}`; figure carries title_position+title_body_gap_lines; table carries group/part/is_continuation/continuation_marker (+continued_from when present) — compatible with the existing compare contract.
- artifacts:
  ```
  artifacts/detector_rtm/
    detected_manifest.json
    compare/compare_report.json
    compare/compare_report.md
    overlay/overlay_manifest.json   (only when compare has failures)
    overlay/index.md
    overlay/<case>/page_NNN_*.png
  ```
- schema validation: `validator.validate_manifest()` returns violations; `writer.write_manifest()` refuses to persist an invalid manifest; the runner validates before compare.

## 6. Validation result
- tests: 14 D10 tests pass.
  - schema: valid passes; wrong schema_version / coordinate_origin / coordinate_unit / missing producer / missing figure region / bad title_position / missing table group → fail; writer refuses invalid.
  - runner: unavailable → exit 2 (not faked); enumerate rtm_frozen 49 + synthetic perfect → compare pass, exit 0; detector-cmd perfect → pass; detector-cmd +30pt caption shift → compare fail, exit 1, overlay generated; contract-invalid detector output → rejected (exit 2).
- compare: integration confirmed — perfect adapter 49/49 pass; shifted adapter fails within the harness.
- overlay: generated on failures (failures-only), manifest+index+PNG present.

## 7. Did not touch
- rtm_frozen: not modified (read-only golden source)
- RTM scenario: not added
- truth schema: not changed
- compare tolerance: not changed

## 8. Known limitations
- real detector algorithm status: NOT implemented. The runner needs either a real `--detector-cmd` or the `--synthetic-from-truth` adapter.
- correctness claims: NONE. `--synthetic-from-truth` is explicitly a contract test (producer.mode=`synthetic-contract-test`); a passing compare there only proves the path + frozen truth are self-consistent, not that any detector is correct.
- Real detector acceptance is a later milestone: a `detector-output-v0` emitter run against rtm_frozen 49, reducing compare failures within tolerance.

Commit `c6db6b6` on `picker-cmc-d03` (after Gate B promotion `4f56397`).
Requesting D10 acceptance and the detector-integration milestone conditions.
