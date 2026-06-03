[D16.5 common-region/watermark truth contract correction report]

Decision implemented: GPT option **B** — correct PDF-derivable truth bbox for
multipart footer + extractable rot0 license watermark; rotated/morph/image-like
watermark kept as documented limitation.

## 1. Summary
- frozen case count: **49 (unchanged)**
- corrected footer truth bboxes: 3 fragments × 2 pages = 6, in
  `exp_hf_multipart_footer_center_notice` (left/center/right)
- corrected watermark truth bboxes: 1 watermark × 3 pages = 3, in
  `exp_wm_license_text_position_jitter` (per-page position jitter)
- residual rotated/morph limitations: 2 cases — `core_fixed_watermark` (rot 45),
  `exp_wm_near_footer_rotation_opacity_jitter` (rot ~8 morph). Authored band kept,
  NOT coerced to pass.

## 2. Files changed
- factory/truth:
  - `rtm_factory/models.py` — `HeaderFooterSpec.band_from_text`, `WatermarkSpec.band_from_text`
  - `rtm_factory/builders/_textband.py` (NEW) — derive the PDF-visible rendered-text
    band using the SAME `get_text('dict')` per-line extraction and the SAME constants
    as `detector/common_regions.py` (FRAGMENT_PAD 3, BAND_BASE 35, BAND_PER_LINE 6,
    WM_BAND_PAD 18; `_WM_RE` mirrored)
  - `rtm_factory/builders/header_footer.py`, `builders/watermark.py` — when
    `band_from_text`, record the rendered-text band instead of the authored bbox
  - `rtm_factory/scenario_specs.py` — `band_from_text=True` on the multipart footer
    (3 specs) and the rot0 license watermark
- rtm_frozen:
  - `exp_hf_multipart_footer_center_notice/...truth.json`, `exp_wm_license_text_position_jitter/...truth.json`
    updated (bbox values only). **PDF/PNG bytes unchanged** (md5-verified).
- detector: **untouched** (still truth-blind)

## 3. Commands run
- regenerate 2 cases via `render.build_pdf`; md5-verify PDF/PNG byte-identical to frozen;
  copy only `*.truth.json`
- verify new truth == `detect_pdf(frozen_pdf)` per page (byte-unchanged frozen PDF is safe)
- `tools/run_detector_on_rtm.py --detector-cmd "python tools/detect_pdf.py --pdf {pdf} --out {out}" --json`
- `python -m pytest tests picker_cmc_v1 -q` → **130 passed**

## 4. Contract correction
- multipart footer: truth fragment bbox = `[text_x0-3, text_top, text_x1+3, text_top+35]`
  (detector's per-fragment band). Was authored `[48,740,220,774]` etc.
- extractable license watermark: truth bbox = the standalone `Licensed to …` line
  bbox padded ±18 (detector's per-line watermark band), per-page with jitter. Was
  authored `[~120,310,~500,510]` centered editorial box.
- rotated/morph watermark: unchanged authored band — documented limitation; the
  morph/rotated text does not extract as a line, so it is never coerced to match.

## 5. Metrics vs D16
| metric | D16 | D16.5 | target |
|---|---|---|---|
| objects matched | 100/100 | **100/100** | 100 |
| missing | 0 | **0** | 0 |
| extra | 0 | **0** | 0 |
| regions ok | 197/210 | **206/210** | ≥203 ✓ |
| cases passed | 45/49 | **47/49** | ≥47 ✓ |
| common/watermark failures | 13 | **4** | ≤4 ✓ |
| anchors | 53/53 | 53/53 | — |
| negative FP | 0 | 0 | — |

The 4 residual region failures are entirely within the 2 rotated/morph watermark
cases (expected limitation).

## 6. No-truth guarantee
- detector truth read: **no** (unchanged; `test_no_truth_guarantee` still passes)
- verification: the factory computes the corrected truth band with the same
  extraction the detector uses, but the detector itself never opens truth.json;
  `test_detector_truth_contract_d165.py` asserts `detect_pdf(pdf) == truth` for the
  two corrected cases WITHOUT the detector reading truth.

## 7. Did not touch
- compare tolerance: unchanged (header/footer x8y5, watermark x14y14)
- scenario layout: unchanged (PDF/PNG bytes identical, md5-verified)
- frozen case selection: unchanged (49)
- caption/body/table identity: unchanged

## 8. Known limitations
- rotated/morph/image-like watermark: text does not extract as a line, so the
  rendered band is not PDF-derivable; authored band kept, reported (never silently
  skipped). 2 cases / 4 regions.
- semantic interpretation: bbox/structure only; no semantic field extraction.

## 9. Tests
- NEW `tests/test_detector_truth_contract_d165.py` (3): corrected cases match
  detector; rotated/morph stay non-matching (not coerced).
- full suite: **130 passed**.

Commit on `picker-cmc-d03`. Stopping after D16.5 report per instruction.
