# [D6 RTM pytest full integration report]

Scope: handoff D6 — bind the RTM factory/promotion/compare/overlay/CLI into a
reproducible pytest gate, plus the two D5.5 cleanups. NOT a detector; no
detector wiring, no scenario expansion, no tolerance/truth-schema changes.

    pytest green != detector correctness on real documents

## 1. Summary
- tests added: `tests/test_rtm_full_integration_d6.py` (4) + `tests/test_rtm_cli_subprocess_d6.py` (4) = 8
- total tests: 45 (was 37)
- integration coverage: full gallery generation, self-check (coverage + text overlap), promotion (index.md-driven), compare pass/fail, overlay artifacts, CLI subprocess + argparse-JSON

## 2. Files changed
- `rtm_factory/cli.py`            D5.5 cleanup: argparse errors → JSON when --json (custom _JsonAwareParser); seed threaded into generate_gallery + result
- `rtm_factory/gallery.py`        manifest now records `generation.seed` + note
- `generate.py`                   passes SEED to write_manifest
- `pytest.ini`                    NEW — registers `slow` + `rtm_integration` markers (no marker warnings)
- `tests/test_rtm_full_integration_d6.py`  NEW — gallery/promote/compare/overlay gates
- `tests/test_rtm_cli_subprocess_d6.py`    NEW — real subprocess CLI gates
- `.gitignore`                    +D6 handoff tarball
- detector / truth schema / compare tolerance / scenario set: unchanged

## 3. Commands run
- `python -m pytest tests -q` → 45 passed
- `python -m pytest tests -q -m "not slow"` → 40 passed, 5 deselected
- `python -m pytest tests -q -m rtm_integration` → 8 passed, 37 deselected
- no PytestUnknownMarkWarning

## 4. D5.5 cleanup
- argparse --json error handling: `_JsonAwareParser.error()` raises instead of printing; `main()` detects `--json` in argv before parsing and emits `{"ok":false,"error_code":"INVALID_INPUT","message":<argparse msg>}` to stdout, exit 2. Verified for `compare --json` (missing required), `no-such-command --json` (invalid choice), `overlay --pages abc --json`.
- seed provenance: `MANIFEST.json.generation = {"seed": 1234, "note": "v0 scenarios are a deterministic fixed set; seed is recorded for provenance and does not alter the generated cases (reserved for future jitter/randomized expansion)."}`; CLI `generate` result also returns `seed`. So seed is no longer silently ignored.

## 5. Pytest gates
- full gallery generation (slow): build into tmp; MANIFEST + index exist; 30–50 cases (42); coverage missing/below_min empty; generation.seed==1234; SELF_CHECK_REPORT text_overlap failures==[]; sample PDF/truth/notes/PNG present.
- self_check: exercised via the gallery gate + CLI `self-check` (coverage + text-overlap summary, passed True).
- promotion: copy gallery → mark keep on 3 cases in index.md keep/drop column → promote → frozen contains exactly those 3, gallery copy unchanged, frozen MANIFEST selected_count=3/dropped_count=39.
- compare: synthetic detected from gallery truth — perfect → exit 0; caption+body y+30pt → exit 1; missing figure → exit 1; extra figure → exit 1 (default); `--allow-extra` extra-only → exit 0.
- overlay: failing compare report → overlay renders only the failed page (failures-only default), overlay_manifest.json + index.md exist, overlay PNG has magic bytes, failures_drawn>0.
- CLI subprocess: real `python rtm_cli.py …` for list-scenarios / generate / generate-case / self-check / compare / overlay (all --json, parsed from stdout, correct exit) + argparse-JSON error cases.

## 6. Validation result
- pass/fail: PASS — 45 passed
- negative tests: compare y-shift/missing/extra → exit 1; argparse missing-args / unknown-command → pure JSON exit 2
- generated artifacts location: all under pytest `tmp_path` (no repo pollution); demo artifacts/ and rtm_frozen_demo/ remain gitignored

## 7. Did not touch
- detector code: not touched (none exists)
- rtm_frozen durable fixtures: none committed (real set still awaits human Gate B; rtm_frozen_demo/ gitignored)
- truth schema: unchanged
- compare tolerance: unchanged
- scenario expansion: none (still 42); no header/footer jitter

## 8. Known limitations
- The module-scoped gallery fixture builds the full 42-case gallery once per run (~3s); `-m "not slow"` still builds it (fixture isn't marked slow) but skips the heaviest standalone gates.
- Subprocess tests assume `rtm_cli.py` is runnable from FACTORY_DIR with the ambient interpreter (PyMuPDF + PyYAML present), matching the dev/CI environment.
- This gate proves the factory pipeline is reproducible; detector acceptance still requires a real detector compared against a human-approved frozen set (future work).

Stopping after D6 as instructed. The RTM factory milestone (D2→D6) is complete; awaiting next direction.
