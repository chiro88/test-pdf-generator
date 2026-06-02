# [Gate B RTM frozen promotion report]

## 1. Summary
- selected_count: **49** (matches expected 49)
- dropped/deferred_count: **24** (matches expected 24)
- frozen output path: `picker_cmc_v1/tests/fixtures/rtm_frozen/`
- selection_source: `index.md` (index-driven; no --keep override)

## 2. Files changed
- `rtm_gallery/index.md` — keep/drop review column filled from your recommendation (49 keep / 24 defer); gallery itself untouched otherwise (gitignored/regenerable).
- `docs/rtm/GateB_keep_drop_recommendation.csv` — your per-case decision, committed for provenance.
- `picker_cmc_v1/tests/fixtures/rtm_frozen/` — NEW durable golden fixtures: `MANIFEST.json` (rtm-frozen-v0, selection_source=index.md, selected_count=49, dropped_count=24), `index.md` (frozen list), and per case PDF + truth.json + notes.md + page PNG(s). Committed (commit 4f56397).

## 3. Commands run
- `python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --json` → `{"ok":true,"selected":[49],"dropped":[24],"selection_source":"index.md"}` exit 0
- validation: read `rtm_frozen/MANIFEST.json` → schema rtm-frozen-v0, selected_count=49, dropped_count=24; on-disk case dirs = 49

## 4. Frozen coverage (49 cases)
- core: 8 (all)
- negative: 6 (all)
- sequence (figure/table x-y band stress): 10 (figure-figure, figure-{1,2}line-text-figure, figure-table, table-figure, table-table, table-{1,2}line-text-figure, figure-{1,2}line-text-table)
- title-gap matrix: 10 (figure & table x above/below x gap 0/1/2 representatives)
- header/footer-combined sequence: 3 (2-line header, footer bar+2 lines, jittered header+footer)
- common-region / jitter: 6 (multipart footer, even/odd mirror+jitter, rule-y jitter, license-text position jitter, near-footer rot/opacity jitter, partial footer support)
- representative figure/table stress: 6 (two-column multi-figure, caption-above wide table, multiline multi-figure, 3-part continuation, second wide table, same-page fragment)

24 defer cases (suffix variants, header-only/footer-only simple variants, watermark simple variants, figure/table shape variants already covered) are held for a later frozen set if the detector is weak on a given axis.

## 5. Did not touch
- detector: not touched (none exists)
- scenario specs: unchanged (still 73 generated)
- truth schema: unchanged
- compare tolerance: unchanged
- CLI: unchanged (used existing `promote`, index.md driven)

## 6. Known limitations
- This RTM frozen set validates **region/band detection** (figure/table caption/body/context x-y bands, ordering, non-target interstitial text). It does **not** validate downstream waveform/diagram/table **semantic interpretation** quality — bodies are synthetic placeholders for band geometry, not real signals/data.
- Next action is detector integration (a `detector-output-v0` emitter), then `compare --truth-root rtm_frozen` within tolerance. That is a separate milestone; not started.

Commits: D9 `6f2378e`→`21cd8ad`→`6463f53`; Gate B promotion `4f56397` on `picker-cmc-d03`.
