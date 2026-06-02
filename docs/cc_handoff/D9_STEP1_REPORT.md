# [D9 step 1 report] Target-aware body filler — truth contamination fixed

Addresses the blocker you flagged: generic paragraph text drawn at fixed y
overlapped figure/table truth regions (97 hits / 22 cases), contaminating the
answer key. This is the "먼저 해결" item before any sequencing work.

## What changed
- **render.py** — `_add_body_filler` is now **target-aware**: it computes the
  figure/table/negative context rects on each page, carves the free
  interstitial y-bands around them (`layout.free_y_bands`), and fills ONLY those
  bands. Text is sized to the band so it actually renders (no
  overflow-renders-nothing). It no longer paints a fixed full-column block.
- **models.py / truth.py** — truth now records, per page,
  `non_target_text_regions` (the interstitial body bands, `kind:
  "non_target_text"`), and per case `intentional_overlap_stress`. This lets a
  detector verify "this 1-line interstitial text is NOT a target."
- **self_check.py** — NEW gate: generic body text overlapping ANY target
  caption/body/context region → **fail** (unless `intentional_overlap_stress=true`).
  Count persisted in `SELF_CHECK_REPORT.json.generic_text_target_overlaps`.
- **layout.py** — `merge_intervals` / `free_y_bands` helpers.

## Evidence
```
before (your review):  generic-text ↔ target overlap = 97 hits / 22 cases
after  (this commit):  generic-text ↔ target overlap = 0 hits / 0 cases
non_target_text_regions recorded: 99
generate -> 50 cases, text-overlap 118/118 matched, self_check PASS
pytest tests -q -> 45 passed
```
Visual: `core_figure_caption_top.p01.png` now shows the caption above a clean
diagram body, with the body paragraph sitting in the free band BELOW the figure
context — no text crosses the figure. (sample PNG attached)

## Did NOT do yet (still rejected as frozen; awaiting your go-ahead)
The remaining D9 items are sequencing/realism, planned next:
- (3) figure/table sequence cases (figure-figure, figure-Nline-text-figure, figure-table, table-figure, table-table, table-text-figure, figure-text-table)
- (4) title/caption position combos + 0/1/2-line gap
- (5) 2-line header (chapter_title / chapter.subsection), odd/even position, footer bar + 2 lines, jitter combined with figure/table cases
- (6) extend coverage taxonomy + self_check for the above
- a band-based page layout engine (header / body-flow / target / interstitial / footer) to drive the sequence cases deterministically

Current case count stays 50; sequence cases will likely require raising the
30–50 gate — I'll confirm the new cap with you before exceeding 50.

## Did not touch
detector code · compare tolerance · CLI · rtm_frozen durable (still empty; current gallery NOT promoted).

Commit `6f2378e` on branch `picker-cmc-d03`. Requesting: confirm the
target-aware approach + truth `non_target_text_regions`, and green-light the
sequence-case expansion (and the new case-count cap).
