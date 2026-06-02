# [D3.5 RTM truth extraction self-check report]

Scope: handoff T2.1 — verify truth text-regions overlap real PyMuPDF
`get_text("dict")` extraction; plus the .gitignore/frozen policy fix. No
detector / compare / overlay / pytest-3 work.

## 1. Summary
- total cases checked: 42 (all)
- text-region overlap checks: 92 regions checked, 92 matched, 0 failures
- skipped checks with reasons: 5 (all rotated/morph watermarks — recorded, not silent)
- failures: 0
- Found & fixed 2 REAL bugs: `exp_figure_above_diagram_dotted` and `exp_figure_multi_raster_multiline` had multiline captions that did not render (text overflowed a 26pt caption box, so PyMuPDF drew nothing). The previous self_check missed this; the new overlap check caught it. Fixed by enlarging those caption boxes (cap_h=46).

## 2. Files changed
- `rtm_factory/self_check.py`  — add `check_text_overlap()` + helpers (_spans/_iou/_center_in/_y_overlap/_match_region); integrate into run_self_check; write `rtm_gallery/SELF_CHECK_REPORT.json`; run_self_check now returns the report.
- `generate.py`               — print text-overlap summary (passed/checked/skipped).
- `scenario_specs.py`         — cap_h=46 for the 3 multiline figure captions so they actually render.
- `.gitignore`                — stop blanket-ignoring rtm_frozen/; ignore only rtm_frozen_demo/ (Option A).
- Unchanged: coverage.py, promote.py, builders/*, detector (none exists).

## 3. Commands run
- `python generate.py` → "generated 42 ... text-overlap self-check: 92/92 regions matched, 5 skipped"
- `python -m pytest tests/ -q` → 8 passed
- negative proof: a 3-line caption forced into an 8pt box → overlap gate reports failure (gate is not a rubber stamp)

## 4. Self-check behavior
- checked region kinds: header, footer, watermark (upright only), figure caption_region, table caption_region. Figure/table BODY regions are not text-checked (raster/vector/diagram by design).
- match rule (lenient on geometry, strict on identity): a region passes iff an extracted span overlaps it (IoU>0, or either center inside the other, within 3pt tolerance) AND the aggregated overlapping text contains the expected key (figure/table index, or header/footer/watermark text, normalized). This rejects "overlaps unrelated filler prose" false positives while tolerating font/wrap jitter. caption/header/footer also require y-overlap.
- skip policy: watermarks with |rotation|>0 (diagonal/morph) extract unreliably and are skipped WITH a reason string recorded in SELF_CHECK_REPORT.json["text_overlap"]["skipped"]; never silently. Upright/image-like watermarks (rot=0) ARE checked (they draw real text via insert_textbox).
- failure message example: `exp_x p1 figure 9.9 caption_region: no extracted text overlaps region; expected_key='9.9' expected_bbox=[...]` and (mismatch form) `... overlapping text '...' lacks expected key; expected_key='3.4' ...`

## 5. .gitignore / frozen policy
- rtm_frozen durable commit policy: `picker_cmc_v1/tests/fixtures/rtm_frozen/` is now commit-eligible (no blanket ignore). It will hold the real, human-reviewed (Gate B) golden fixtures committed without `git add -f`.
- demo output policy: the non-approved `--keep` demo set is written to `picker_cmc_v1/tests/fixtures/rtm_frozen_demo/`, which is gitignored. The earlier demo at rtm_frozen/ was deleted.

## 6. Results
- generate.py: 42 cases, self_check PASS, 92/92 overlap matched, 5 skipped
- self_check: PASS (coverage gate + text-overlap gate); SELF_CHECK_REPORT.json written
- tests: `tests/` 8 passed (test_rtm_factory_generation x3, test_rtm_promote_d3 x5)

## 7. Did not touch
- detector code: not touched (none exists)
- compare harness: not started (D4)
- overlay/diff: not started (D5)
- pytest-3 full suite: not built (D6)

## 8. Known limitations
- Rotated/morph and the rotated portion of diagonal watermarks are not text-verified (extraction unreliable); recorded as explicit skips. Their bbox/rotation_deg are still schema- and bounds-checked.
- The overlap key for header/footer is the exact truth text; if a future header template renders glyphs PyMuPDF can't extract, it would surface as a (correct) failure to investigate, not a silent pass.
- Real rtm_frozen remains empty until human Gate-B review of index.md.

Stopping after D3.5 as instructed. Awaiting accept/reject before D4 (`compare_detector_to_truth.py`).
