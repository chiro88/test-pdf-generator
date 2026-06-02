# RTM Factory v0 Handoff to cc-coder

## Mission

Complete the `pdf-yband-picker` Real Tracking Mock (RTM) PDF fixture system from the provided v0 baseline.

The goal is to prevent meaningless mock-only pass reports. Detector work is not acceptable unless it can be tested against real PDF files generated or frozen by this RTM system.

## Starting point

The baseline code is under:

```text
picker_cmc_v1/tests/fixtures/rtm_factory/
  generate.py
  rtm_factory/
    models.py
    templates.py
    layout.py
    scenario_specs.py
    builders/
      header_footer.py
      watermark.py
      figure.py
      table.py
      negative.py
    render.py
    truth.py
    self_check.py
    gallery.py
```

Generated candidate output is under:

```text
picker_cmc_v1/tests/fixtures/rtm_gallery/
```

Run:

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory
python generate.py
```

Current v0 creates 19 candidate cases and runs self-check.

## Non-negotiable contracts

### Coordinate system

Every bbox must be:

```text
[x0, y0, x1, y1]
origin = page TOP-LEFT
y increases downward
unit = pdf_pt
```

Do not use PDF-native bottom-left coordinates in truth JSON.

### Truth enum and field names

Use exactly:

```text
kind ∈ {figure, table, header, footer, watermark}
```

For figures and tables, use:

```text
caption_region
body_region
context_region
```

Do not add caption/body/context as sub-kind enums.

### Detector pass separation

Do not claim detector correctness from RTM factory self-check.

```text
factory self-check pass = generated PDFs/truth/previews are internally valid
detector pass = detector output matches frozen truth JSON within tolerance
```

## Required completion tasks

### T1. Expand scenario coverage

Current v0 has 19 cases. Expand the generated candidate set to:

```text
core set: exactly/at least 8 required core scenarios
negative set: at least 5 false-positive resistance scenarios
expanded set: 30-50 representative cases
```

Do not generate full Cartesian explosion. Use a deterministic representative covering set.

Every major axis value should appear at least twice unless explicitly documented as a rare one-off stress case.

Required axis values:

```text
page:
  size: letter, a4
  orientation: portrait, landscape
  columns: single, two-column
  pages: 1, 3, 8
  page_offset: 0, nonzero

header/footer:
  none
  header only
  footer only
  both
  even/odd mirrored
  page number variable
  subtitle variable
  rule line present
  partial support ratio

watermark:
  none
  fixed text
  variable text
  center
  corner
  light opacity
  strong opacity
  rotation 0
  rotation 45 or diagonal morph fallback
  image-like watermark

figure:
  caption below body: figure_body_direction=up
  caption above body: figure_body_direction=down
  aliases: Figure, Fig., FIGURE
  indexes: 3.4, 12, 2-7, A.1
  one-line title
  multiline title
  raster body
  vector/diagram body
  waveform body
  mixed body
  column-width
  page-wide
  multiple figures per page

table:
  single page
  multipage continuation, 2-4 parts
  suffixes: (cont), (continued), continued, Continued, cont.
  same title repeated but different groups
  different titles
  same-page fragment
  normal width
  wide table
  caption above body: table_body_direction=down

negative:
  ordinary text page
  Figure of merit ...
  see Table above ...
  Figure 3.4 is referenced ... without figure
  Table 2.1 describes ... without table
  weak partial header
```

### T2. Upgrade self-check

`self_check.py` must also verify:

1. Text-based truth regions overlap or contain the text extraction bboxes from `page.get_text("dict")`.
2. A diagonal watermark case exists and is not silently skipped.
3. Each declared axis value has coverage count >= 2, except explicit exceptions.
4. Every core scenario is present by exact name.
5. Every negative scenario is present by exact name.
6. Alpha index `A.1` appears in at least two figure/table-related cases.
7. Continuation suffix cases cover all standard suffixes:
   - `(cont)`
   - `(continued)`
   - `continued`
   - `Continued`
   - `cont.`
8. `MANIFEST.json` contains a machine-readable coverage summary.

### T3. Add frozen fixture promotion

Generated candidates must not be used directly as detector golden fixtures.

Add a promotion script:

```text
picker_cmc_v1/tests/fixtures/rtm_factory/promote_keep_cases.py
```

Input:

```text
picker_cmc_v1/tests/fixtures/rtm_gallery/index.md
```

Behavior:

- Read manually filled keep/drop decisions.
- Copy keep cases to:

```text
picker_cmc_v1/tests/fixtures/rtm_frozen/
```

- Write:

```text
picker_cmc_v1/tests/fixtures/rtm_frozen/FROZEN_MANIFEST.json
```

- Preserve PDF, truth.json, first-page and all-page PNG previews, notes.md.
- Never delete frozen cases automatically.
- If a frozen case changes, require explicit `--replace` and emit a diff summary.

### T4. Add detector golden comparison scaffold

Add a detector comparison harness, even if detector integration is initially an adapter stub:

```text
picker_cmc_v1/tests/fixtures/rtm_factory/compare_detector_to_truth.py
```

Expected behavior:

```bash
python compare_detector_to_truth.py \
  --frozen-dir picker_cmc_v1/tests/fixtures/rtm_frozen \
  --detector-cmd "python -m picker_cmc.detect --setup {setup} --pdf {pdf} --out {out}" \
  --artifacts-dir artifacts/rtm_compare
```

Comparison requirements:

```text
page index: exact
kind: exact
figure/table index: exact
caption y0/y1 tolerance: <= 5 pt
body y0/y1 tolerance: <= 8 pt
context y0/y1 tolerance: <= 10 pt
x0/x1 tolerance: <= 10 pt unless case says strict_x
vertical overlap ratio: >= 0.85 for body/caption bands
table_group_id: exact for continuation cases
part_index: exact for continuation cases
is_continuation: exact
continuation_marker: normalized exact
```

Output artifacts on every run:

```text
artifacts/rtm_compare/<case_id>/
  detected_manifest.json
  truth.json
  diff_report.md
  page_001_overlay.png
  page_002_overlay.png
  ...
```

### T5. Add overlay renderer

Implement overlay visualization for human review:

```text
picker_cmc_v1/tests/fixtures/rtm_factory/rtm_factory/overlay.py
```

Overlay requirements:

- Draw truth regions and detector regions on page preview.
- Distinguish header, footer, watermark, figure, table.
- Draw caption/body/context separately.
- Use labels with kind/index/part.
- In failure reports, include at least the pages with mismatches.

### T6. Add pytest integration

Add tests:

```text
tests/test_rtm_factory_generation.py
tests/test_rtm_frozen_fixtures.py
tests/test_rtm_detector_compare_contract.py
```

Minimum checks:

- `generate.py` creates all expected files.
- `self_check` passes.
- frozen manifest is parseable if present.
- truth schema fields match project contract.
- comparison code rejects obvious wrong bbox output.
- comparison code accepts within-tolerance bbox output.

### T7. Preserve modular design

Do not collapse this into one giant script.

Required design rules:

- Keep `CaseSpec` / `PageSpec` / `HeaderFooterSpec` / `WatermarkSpec` / `FigureSpec` / `TableSpec` object model.
- Add scenario cases by data/spec objects, not by massive nested `if/else` blocks.
- Builders must stay separated by domain: header/footer, watermark, figure, table, negative.
- Layout helpers belong in `layout.py`.
- Truth serialization belongs in `truth.py`.
- Gallery/index creation belongs in `gallery.py`.
- Self-check belongs in `self_check.py`.
- Detector comparison belongs in a separate module; do not mix it into generation.

## Definition of Done

The task is complete only when all of these pass:

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory
python generate.py
python -m pytest tests/test_rtm_factory_generation.py tests/test_rtm_detector_compare_contract.py
```

And the generated gallery satisfies:

```text
- 8 core scenarios present
- >= 5 negative scenarios present
- 30-50 expanded scenarios present
- every major axis value appears >= 2 times or has explicit exception
- MANIFEST.json includes coverage summary
- index.md includes empty human review columns
- every case has PDF + PNG preview(s) + truth.json + notes.md
```

No detector implementation may be accepted from now on unless it is tested against frozen RTM fixtures or an explicitly approved real-PDF fixture set.
