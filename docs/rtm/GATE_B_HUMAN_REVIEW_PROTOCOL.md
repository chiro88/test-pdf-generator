# Gate B — Human Review Protocol

Gate B is the **human** step between generated candidates (`rtm_gallery`) and
the durable golden set (`rtm_frozen`). The factory cannot promote anything until
a person decides which cases are realistic enough to freeze.

> Do **not** keep all 50 cases blindly. The frozen set is the detector's golden
> truth; weak or unrealistic cases will distort detector evaluation.

## Step 1 — Generate / refresh the gallery

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory
python rtm_cli.py generate --out ../rtm_gallery --json
python rtm_cli.py self-check --gallery ../rtm_gallery --json   # must report passed=true
```

This writes `rtm_gallery/index.md` (the review form) plus, per case, a PDF, a
`.truth.json`, page preview PNG(s), and a `.notes.md`.

## Step 2 — Open the review form

Open `picker_cmc_v1/tests/fixtures/rtm_gallery/index.md` in a Markdown viewer
that renders the thumbnail images. Each row is one case:

```
| case_id | thumbnail | axis tags | realism 1-5 | keep/drop | critique |
```

For deeper inspection of a case, open its full preview(s) and PDF:

```
rtm_gallery/<case_id>/<case_id>.p01.png   # first-page preview (p02, p03… for multipage)
rtm_gallery/<case_id>/<case_id>.pdf        # the actual candidate PDF
rtm_gallery/<case_id>/<case_id>.notes.md   # what the case is meant to exercise
```

## Step 3 — Fill the three review columns

Fill these by hand, one row at a time:

- **realism 1-5** — how plausible this looks as a real datasheet/manual page.
  - 5 = indistinguishable from a real page; 3 = plausible but synthetic-looking; 1 = clearly artificial.
- **keep/drop** — type exactly `keep` (case-insensitive) to promote it; leave blank or `drop` to exclude. Only `keep` is promoted.
- **critique** — short note: what's unrealistic, what to fix, or why you kept/dropped it.

What to look for:
- caption/body/context regions sit where a human would expect them;
- header/footer/watermark land in plausible bands;
- jitter cases still look like a stable running header (small wobble, not chaos);
- multi-part footers read as left/center/right, not overlapping;
- negative cases genuinely have no real figure/table to detect.

See `GATE_B_SELECTION_CHECKLIST.md` for the recommended keep set and minimum counts.

## Step 4 — Promote the kept cases

```bash
python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --json
```

- Promotion is **copy-only**; `rtm_gallery` is never modified.
- Default is **index.md driven** (only `keep` rows). Existing `rtm_frozen` fails unless `--force`; 0 keep fails unless `--allow-empty`.
- For a quick override (e.g. scripted demo), `--keep id1,id2` selects explicitly; the real review is index.md.

The frozen set lands at `rtm_frozen/` with `MANIFEST.json` (schema
`rtm-frozen-v0`, `promotion.selected_count`/`dropped_count`) + a frozen
`index.md` + each kept case's PDF/truth/notes/PNGs.

## Step 5 — Validate the frozen set

```bash
python rtm_cli.py compare --truth-root ../rtm_frozen --detected <detected.json> --out artifacts/rtm_compare --json
python rtm_cli.py overlay --truth-root ../rtm_frozen --detected <detected.json> \
  --compare-report artifacts/rtm_compare/compare_report.json --out artifacts/rtm_overlay --json
```

(These require a detector output manifest. Until a detector exists, you can
sanity-check the harness with a truth-derived synthetic manifest — see the CLI
cheat sheet — but that is a harness check, **not** detector acceptance.)

## Regression lock

Once a case is frozen, do **not** edit its `truth.json` just to make a detector
pass. Truth changes require explicit review and a diff; re-promotion of a changed
case requires `--force` and produces a new manifest.
