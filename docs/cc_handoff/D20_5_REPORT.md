[D20.5 real-PDF body non-target exclusion report]

Narrow fix on the one D20 blocker: dp_sample1 Figure 3-5's body swallowed the
preceding Note block + explanatory paragraph. D20's full diagram/table expansion
is preserved; RTM regression unchanged.

## 1. Summary
- body exclusion changes: the figure body core is now the vertically-contiguous
  drawing band NEAREST the caption (density cluster), so a thin Note separator rule
  across a larger gap above the waveform is split off. Short labels are only pulled
  in when they y-overlap a drawing row (left signal names stay; a Note heading /
  prose above the diagram does not). The caption-column filter now applies only in a
  genuine two-column layout, so a lone wide waveform with a short/offset caption
  keeps its full width (and its left labels).
- affected real-PDF object: dp_sample1 `figure:3-5:page1`.

## 2. Files changed
- `picker_cmc_v1/detector/region_inference.py` — restore `_grow_cluster` (density
  band) for figure cores; `_expand_with_labels` anchors labels to the drawing core's
  y-band; `infer_body` applies the column filter only when a side-by-side same-row
  caption exists.
- `tests/test_detector_body_exclusion_d205.py` (NEW, 6).
- (pipeline / truth / common-region / table-identity / title patterns: untouched.)

## 3. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_review_gate_c/dp_sample1 --json`
- RTM frozen regression runner; `python -m pytest tests picker_cmc_v1 -q` → **185 passed**

## 4. No-truth guarantee
- truth read by detector: **no** (`test_no_truth_guarantee`)
- verification: body inference uses only extracted drawings/text + geometry; no
  truth.json opened; nothing keyed on PDF name/title/case id.

## 5. RTM regression
- cases: 47/49 (unchanged)
- objects: 100/100
- missing: 0 | extra: 0
- regions: 206/210 (4 = pre-existing rotated/morph watermark limitation)
- pytest: 185 passed (179 prior + 6 D20.5)

## 6. Real PDF re-review
- dp_sample1 Figure 3-5 before (D20): `[117, 359, 548, 579]` — included the Note
  heading + explanatory paragraph above the waveform.
- dp_sample1 Figure 3-5 after (D20.5): `[118, 460, 544, 577]` — y0 starts at the
  T0/HCLK waveform; Note + paragraph + "Figure 3-5 shows…" excluded; left signal
  labels (HCLK/HADDR/HWRITE/HRDATA/HREADY/HWDATA) and the full waveform included.
- other objects unchanged (Figure 1-1/1-2/2-2, Tables 1-7/2-1/2-2/3-1, Figures 3-3/3-4
  all still full-body; anchor counts dp_sample 3/3, dp_sample1 3/1).
- accept/bad_body_region estimate: **accept 10/10** (Figure 3-5 now clean); minor_edit
  possible only on tight edges (operator confirmation still required).

## 7. Visual artifacts (regenerated, git-ignored)
- updated crop: `artifacts/real_pdf_review_gate_c/dp_sample1/crops/figure_3-5_body.png`
  (waveform only, no Note/prose)
- updated overlay: `artifacts/real_pdf_review_gate_c/dp_sample1/pages/page_001_overlay.png`

## 8. Did not touch
- rtm_frozen: unchanged
- truth schema: unchanged
- compare tolerance: unchanged
- RTM scenarios: unchanged
- title patterns: unchanged
- common-region contract: unchanged

## 9. Known limitations
- semantic interpretation: geometry only; no table cell / signal semantics.
- real-PDF no ground truth: judged by RTM regression + visual review; operator
  confirmation still required. Rotated/morph watermark remains a documented limitation.

Commit on `picker-cmc-d03`. Stopping after D20.5 report with the updated Figure 3-5 crop/overlay.
