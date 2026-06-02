# Gate B — Selection Checklist

Use this while filling the `keep/drop` column in `rtm_gallery/index.md`. The goal
is a frozen set that is **realistic and representative**, not exhaustive.

## Target size

- **minimum**: 15–25 cases
- **preferred**: 20–35 cases
- **avoid**: auto-keeping all 50

The final selection is the reviewer's call; these are guardrails.

## Must-cover (keep at least one realistic representative of each)

- [ ] **core 8** — keep all 8 if they look realistic (they anchor the corpus)
  - core_fixed_header_footer, core_variable_subtitle_header, core_fixed_watermark,
    core_figure_caption_bottom, core_figure_caption_top, core_multipage_table_cont,
    core_same_title_tables, core_wide_diagram_xrange
- [ ] **negative 6** — keep all 6 (false-positive resistance)
  - neg_plain_text_only, neg_false_figure_of_merit, neg_false_see_table_above,
    neg_caption_reference_only, neg_false_table_reference, neg_weak_partial_header
- [ ] **figure** representatives — caption above & below, ≥2 body kinds (waveform/diagram/raster/mixed), a page-wide figure, multiple-per-page
- [ ] **table** representatives — single-page, a continuation (2–4 parts), a continuation suffix, same-title vs different-title, wide table, same-page fragment
- [ ] **common-region jitter** — at least one header/footer jitter case (xy / rule-y / even-odd)
- [ ] **watermark** — fixed, a diagonal, and at least one jitter/near-footer case
- [ ] **multi-part footer** — exp_hf_multipart_footer_center_notice
- [ ] **first-page suppression** — exp_hf_first_page_suppressed
- [ ] **page-number variety** — bottom-center, bottom-right, "Page x of y"

## Drop / critique guidance

- Drop a case whose **realism ≤ 2** (clearly artificial) unless it covers a unique axis nothing else does — then keep it and note the weakness in `critique`.
- Drop visually broken layouts (overlapping regions, text spilling out of its band).
- If two cases are near-duplicates, keep the more realistic one.
- Always leave a short `critique` note for kept-but-imperfect and for dropped cases (so the choice is auditable).

## After selection — promote and validate

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory

# promote the kept (index.md keep column) cases
python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --json

# confirm the frozen set
python -c "import json; m=json.load(open('../rtm_frozen/MANIFEST.json')); \
print('selected', m['promotion']['selected_count'], 'dropped', m['promotion']['dropped_count'])"

# (when a detector exists) compare its output against the frozen golden truth
python rtm_cli.py compare --truth-root ../rtm_frozen --detected detected.json --out artifacts/rtm_compare --json
python rtm_cli.py overlay  --truth-root ../rtm_frozen --detected detected.json \
  --compare-report artifacts/rtm_compare/compare_report.json --out artifacts/rtm_overlay --json
```

## Frozen hygiene

- Commit the **human-reviewed** `rtm_frozen/` (it is commit-eligible). Do **not** commit `--keep` demo output (that goes to `rtm_frozen_demo/`, gitignored).
- Never auto-delete frozen cases; changing a frozen case requires `--force` and a diff review.
- Re-run `python -m pytest tests -q` after promotion to confirm nothing regressed.
