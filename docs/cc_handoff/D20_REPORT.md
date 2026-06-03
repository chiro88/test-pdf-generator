[D20 real-PDF body_region inference report]

Goal (per GPT): make real-PDF body_region cover the FULL figure/table (unenclosed
diagrams, waveforms with left signal labels, text-heavy table rows) rather than a
caption strip / sub-block, WITHOUT regressing RTM or the no-truth guarantee.

## 1. Summary
- body inference changes: new cluster/ownership body inference in
  `region_inference.py` — body side by per-kind orientation (topmost-caption vote),
  drawings filtered to the caption column AND owned by the nearest caption,
  dominant-frame-or-diagram-union core, transitive short-label inclusion (left
  signal names), and a contiguous row-text body for grid-less tables. The diagonal
  watermark is matched by TEXT (not its huge bbox) so it no longer hides body content.
- real PDF smoke: every flagged object's body now covers the full figure/table.
- RTM regression: unchanged (47/49, 100/100, regions 206/210).

## 2. Files changed
- `picker_cmc_v1/detector/region_inference.py` — `body_orientation`, `_owns`,
  `infer_body` (+ helpers); removed the superseded single-frame `infer_region`/`frames`.
- `picker_cmc_v1/detector/pipeline.py` — call `infer_body` with per-kind orientation
  + all-caption ownership context.
- `tests/test_detector_body_inference_d20.py` (NEW, 7).
- (pdf_extract / truth / common-region / table-identity / title patterns: untouched.)

## 3. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample.pdf  --out artifacts/real_pdf_review_gate_c/dp_sample  --json`
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_review_gate_c/dp_sample1 --json`
- RTM frozen regression runner; `python -m pytest tests picker_cmc_v1 -q` → **179 passed**

## 4. No-truth guarantee
- truth read by detector: **no** (`test_no_truth_guarantee` in D20 + baseline suites)
- verification: body inference uses only extracted drawings/text + page geometry;
  no truth.json is opened; nothing is keyed on a PDF name, title, or case id.

## 5. RTM regression
- cases: 47/49 (unchanged)
- objects: 100/100
- missing: 0  | extra: 0
- regions: 206/210 (4 failures = the pre-existing rotated/morph watermark limitation)
- pytest: 179 passed (172 prior + 7 D20)

## 6. Real PDF results (body w×h, before → after)
- dp_sample figures/tables: 3 figures / 3 tables (anchor counts unchanged)
  - figure 1-1: 134×107 → **426×111** (both device boxes, was the right box only)
  - table 1-7:  504×24  → **490×428** (all rows, was the header strip)
  - figure 1-2: 345×58  → **506×284** (full architecture diagram)
  - figure 2-2: 504×24  → **298×101** (device-box diagram, separated from table 2-2)
  - table 2-2:  504×24  → **329×64**  (the 4 category rows)
  - table 2-1:  504×24  → **487×432** (full table)
- dp_sample1 figures/tables: 3 figures / 1 table
  - figure 3-3: 272×97  → **339×101** (adds the left HCLK/HADDR/HWRITE/HRDATA/HREADY labels)
  - figure 3-4: 204×97  → **272×101** (waveform box)
  - figure 3-5: 487×24  → **427×216** (full multiple-transfer waveform)
  - table 3-1:  487×24  → **485×328** (table rows)
- body crop improvement summary: 8/10 grew ≥1.5× in area; the other two (3-3, 3-4)
  grew in width to include the left signal labels — effectively 10/10 improved.

## 7. Gate C re-review estimate
- previous bad_body_region: 10/10
- now acceptable (accept): ~10/10 (body now covers the full figure/table; see the
  regenerated crops, e.g. dp_sample1 Figure 3-3 with left labels and dp_sample Table 1-7
  with all rows)
- still bad_body_region: 0 expected
- minor_edit: possible on a few edges (e.g. footnote inclusion / a tight diagram edge)
- (operator confirmation still required — no real-PDF ground truth.)

## 8. Visual artifacts (regenerated, git-ignored)
- overlays: `artifacts/real_pdf_review_gate_c/<pdf>/pages/*.png`
- crops: `artifacts/real_pdf_review_gate_c/<pdf>/crops/*.png`
- before/after: §6 above and `GATE_C_OBJECT_LIST_d20.csv`
- bundled samples in the handoff tar: dp_sample Figure 1-1 / Table 1-7 / Figure 1-2,
  dp_sample1 Figure 3-3 / Figure 3-5 / Table 3-1 (overlay + crop each).

## 9. Did not touch
- rtm_frozen: unchanged
- truth schema: unchanged
- compare tolerance: unchanged
- RTM scenarios: unchanged
- title patterns: unchanged
- common-region contract: unchanged (watermark match refined for body-occlusion only,
  no change to common-region detection output)

## 10. Known limitations
- semantic interpretation: geometry only; no table cell / signal semantics.
- rotated/morph watermark: still a documented limitation (the 4 RTM region failures).
- real-PDF no ground truth: improvement judged by RTM regression + visual review;
  operator confirmation still required.

Commit on `picker-cmc-d03`. Stopping after D20 report with visual artifacts per instruction.
