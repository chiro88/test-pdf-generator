# [D8 RTM milestone closeout / Gate B prep report]

Scope: handoff D8 — documentation only (milestone closeout + Gate B human-review
prep). No feature work, no detector, no durable rtm_frozen, no scenario/coverage/
truth/tolerance/CLI changes.

## 1. Summary
- docs added/updated: 5 operations/review documents under `docs/rtm/`
- Gate B status: prepared — protocol + selection checklist authored; awaiting human keep/drop on `rtm_gallery/index.md` (not yet performed; rtm_frozen still empty)
- detector integration status: not started (and explicitly out of D8 scope)

## 2. Files changed
- `docs/rtm/RTM_FACTORY_OPERATIONS.md`            NEW
- `docs/rtm/GATE_B_HUMAN_REVIEW_PROTOCOL.md`       NEW
- `docs/rtm/RTM_MILESTONE_CLOSEOUT_D2_D7.md`       NEW
- `docs/rtm/RTM_AGENT_CLI_CHEATSHEET.md`           NEW
- `docs/rtm/GATE_B_SELECTION_CHECKLIST.md`         NEW
- `.gitignore`                                     +D8 handoff tarball
- no code touched (rtm_factory package unchanged)

## 3. Commands run
- `python -m pytest tests -q` → 45 passed
- `python -m pytest tests -q -m "not slow"` → 32 passed / 13 deselected
- `python -m pytest tests -q -m rtm_integration` → 8 passed / 37 deselected

## 4. Documents
- operations guide: `RTM_FACTORY_OPERATIONS.md` — purpose, file map, rtm_gallery vs rtm_frozen, full command reference, self-check gates, pipeline order, "pytest green != detector correctness".
- human review protocol: `GATE_B_HUMAN_REVIEW_PROTOCOL.md` — generate → open index.md → fill realism/keep-drop/critique → promote → validate; what to look for; regression lock.
- milestone closeout: `RTM_MILESTONE_CLOSEOUT_D2_D7.md` — per-stage table with commit hashes (D2 18fe638 … D7 3e99073), 50-case corpus, coverage axes, self-check result, known limitations, detector prerequisites.
- CLI cheatsheet: `RTM_AGENT_CLI_CHEATSHEET.md` — every command with `--json` sample I/O, exit codes, error codes, scenario file shape, detected manifest shape, harness-sanity snippet.
- selection checklist: `GATE_B_SELECTION_CHECKLIST.md` — target size (min 15–25 / preferred 20–35 / avoid all-50), must-cover boxes, drop/critique guidance, post-promote validation, frozen hygiene.

## 5. Gate B workflow (documented)
- generate: `python rtm_cli.py generate --out <gallery> --json` then `self-check --gallery <gallery> --json`
- human review: open `rtm_gallery/index.md`, fill realism 1-5 / keep-drop / critique per the protocol + checklist
- promote: `python rtm_cli.py promote --gallery <gallery> --out <rtm_frozen> --json`
- validate frozen: inspect `rtm_frozen/MANIFEST.json` (`promotion.selected_count`/`dropped_count`)
- compare/overlay after detector output exists:
  - `python rtm_cli.py compare --truth-root <rtm_frozen> --detected <detected.json> --out <compare_out> --json`
  - `python rtm_cli.py overlay --truth-root <rtm_frozen> --detected <detected.json> --compare-report <compare_report.json> --out <overlay_out> --json`

## 6. Validation result
- pytest: 45 passed
- not slow: 32 passed (13 deselected)
- rtm_integration: 8 passed (37 deselected)

## 7. Did not touch
- detector code: not touched (none exists)
- rtm_frozen durable: not created/committed (awaits human Gate B)
- scenario specs: unchanged (still 50)
- coverage taxonomy: unchanged
- truth schema: unchanged
- tolerance: unchanged

## 8. Known limitations / next required human action
- **Next required action is human**: a reviewer must fill the keep/drop column in `rtm_gallery/index.md` and run `promote` to create the durable `rtm_frozen` golden set. The factory cannot self-approve.
- The CLI cheatsheet's harness-sanity snippet builds a truth-derived synthetic detected manifest; it validates the comparison harness only, never detector correctness.
- Detector integration remains a separate future milestone gated on: completed Gate B, a detector emitting `detector-output-v0`, and a 0-failure `compare` against `rtm_frozen` within tolerance.

Stopping after D8 as instructed. The RTM factory milestone (D2→D8) is documented and closed out; the next step is human Gate B review.
