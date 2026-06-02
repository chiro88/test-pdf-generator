# [D4 RTM detector-vs-truth comparison report]

Scope: handoff T4 / D4 only — a golden comparison *harness* (truth.json vs a
detector output manifest, tolerance-based, JSON+md diff, exit codes). NOT a
detector. No overlay/crop PNGs, no detector code, no D5/D6 work.

    comparison pass != detector correctness on real documents

## 1. Summary
- compare harness: `rtm_factory/compare.py` (logic) + `compare_detector_to_truth.py` (thin CLI)
- tests: `tests/test_rtm_compare_d4.py` — 11 passed
- report outputs: `artifacts/rtm_compare/compare_report.json` + `compare_report.md`

## 2. Files changed
- `rtm_factory/compare.py`              NEW — ToleranceProfile/ComparisonConfig, identity-key extraction, compare_bbox/compare_object/compare_cases, load_truth_cases/load_detected_manifest/write_compare_report
- `compare_detector_to_truth.py`        NEW — thin CLI (exit 0/1/2)
- `tests/test_rtm_compare_d4.py`        NEW — 11 perturbation tests (no real detector)
- `.gitignore`                          +`artifacts/` (regenerable compare output)
- truth schema unchanged; models.py untouched; detector untouched

## 3. Commands run
- `python -m pytest tests/test_rtm_compare_d4.py -q` → 11 passed; full `tests/` → 19 passed
- end-to-end demo (detected synthesized from the 42-case gallery truth):
  - perfect copy → `42/42 cases passed, 0 region failures` → exit 0
  - caption_region y shifted +20pt (tol 5) on one case → `41/42 ... 1 region failures` → exit 1
  - both wrote compare_report.json + compare_report.md

## 4. Input/output contract
- truth input: `--truth-root` dir with MANIFEST.json + `<case_id>/<case_id>.truth.json`. Principle printed at runtime: rtm_gallery = generated candidates / dev comparison only; rtm_frozen = human-reviewed golden source.
- detected input: `--detected` JSON, schema `detector-output-v0`, coordinate_unit=pdf_pt, coordinate_origin=top-left, cases[].pages[].{common_regions, figures, tables}.
- report output: `--out` dir → compare_report.json (summary/failures/cases/config) + compare_report.md.
- exit codes: 0 pass · 1 comparison failed · 2 invalid input/schema.

## 5. Matching and tolerance policy
- identity-key matching FIRST (not bbox), so missing/extra are caught:
  - common regions: (page, kind, ordinal-within-(page,kind))
  - figures: (page, index)
  - tables: (table_group_id, part_index); fallback (page, index, part_index)
- region targets compared: common→bbox; figure→caption/body/context; table→caption/body/context(if present) + fields table_group_id/part_index/is_continuation/continuation_marker/continued_from(exact).
- tolerances (strict default; `--tolerance-profile loose` = 2×): header/footer (x8,y5), watermark (x14,y14), caption_region (x8,y5), body_region (x12,y8), context_region (x14,y10). Each region record carries expected/actual/delta/tolerance/passed.
- pass/fail (strict default): missing expected object → fail; extra detected object → fail (unless `--allow-extra`); wrong index/group/part → fail; bbox outside tolerance → fail; missing schema_version / coordinate_unit≠pdf_pt / coordinate_origin≠top-left → invalid input (exit 2). Dev flags: `--allow-extra`, `--case-id`, `--region-kind`, `--tolerance-profile`; default stays strict.

## 6. Validation result
- pass/fail: PASS (harness behaves to contract)
- negative tests (all assert failure/invalid as required):
  1. identical detected → pass (3 objects matched, 0 region fails)
  2. caption y shifted beyond tol → fail
  3. caption x shifted within tol → pass
  4. missing figure / table / common region → fail (objects_missing≥1)
  5. extra detected object → fail by default
  6. `--allow-extra` → extra-only → pass
  7. wrong table_group_id → fail (missing+extra via identity key); wrong continuation_marker → field fail
  8. coordinate_unit/origin mismatch & missing schema_version → InvalidInput (exit 2)
  9. compare_report.json + compare_report.md created, JSON has summary/failures/cases

## 7. Did not touch
- detector code: not touched (none exists)
- overlay/diff images: not created (D5)
- pytest-3 full integration: not built (D6)
- rtm_frozen durable fixtures: none committed (still awaits human Gate B; only rtm_frozen_demo/ exists, gitignored)

## 8. Known limitations
- Without a real detector, validation uses truth-derived synthetic detected manifests; real detector wiring is D-later.
- Identity-key table matching means a wrong table_group_id/part_index surfaces as missing+extra (still a fail) rather than a field-level diff; intentional, and continuation_marker/is_continuation/continued_from ARE field-compared once keys match.
- Per your D3.5 note: detector-stage matching may later want index + title prefix + region type together; D4 matches by index/group/part (sufficient for the golden gate). Rotated/morph watermark skips remain recorded upstream in self_check, not silently dropped.

Stopping after D4 as instructed. Awaiting accept/reject before D5 (overlay.py / diff artifacts).
