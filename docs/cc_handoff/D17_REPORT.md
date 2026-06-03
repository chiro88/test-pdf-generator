[D17 real-PDF smoke / operator review harness report]

Goal (per GPT): user-supplied real PDF → detect_pdf → detector-output-v0 →
visual overlay/review package → operator confirms figure/table x/y-bands. This is
NOT a real-PDF correctness pass; there is no truth, so the result is a review
artifact.

## 1. Summary
- runner: `tools/run_detector_on_pdf.py` (single PDF → review package; `--json`)
- review artifacts: `detected_manifest.json` (detector-output-v0, validator PASS),
  `review_index.md`, `summary.json`, `pages/page_NNN_overlay.png`,
  `crops/<figure|table>_<index>_body.png`
- real PDF smoke status: **works** on a local sample (VESA DP spec, 6 pages):
  3 figures, 3 tables, 43 common regions, 3 watermarks detected; overlays+crops
  generated; manifest validates. No correctness claim.

## 2. Files changed
- `picker_cmc_v1/detector/review_artifacts.py` (NEW) — `build_review_package()`:
  detect → contract-valid manifest → per-page overlays → figure/table body crops →
  `review_index.md` → `summary.json`. Self-contained drawing (no truth, no compare,
  no rtm_factory dependency); nothing case-specific.
- `picker_cmc_v1/tools/run_detector_on_pdf.py` (NEW) — thin CLI, `--json`, structured
  error on bad input.
- `tests/test_real_pdf_smoke_runner_d17.py` (NEW, 6) — synthetic-PDF smoke tests.
- `.gitignore` — ignore `pdf/` (user PDFs) and the D16.5/D17 handoff bundles;
  `artifacts/` (review packages, may render copyrighted PDFs) already ignored.

## 3. Commands run
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample.pdf  --out artifacts/real_pdf_smoke/dp_sample  --json`
- `python tools/run_detector_on_pdf.py --pdf ../pdf/dp_sample1.pdf --out artifacts/real_pdf_smoke/dp_sample1`
- `python -m pytest tests picker_cmc_v1 -q` → **136 passed**
- RTM frozen regression runner (unchanged metrics, see §5)

## 4. Input/output contract
- input PDF: arbitrary user PDF (read-only artifact source; not committed)
- output manifest: `<out>/detected_manifest.json` — `detector-output-v0`, validator PASS
- review index: `<out>/review_index.md` — PDF path, page count, per-page overlay links,
  per figure/table (page, type, index, title, caption/body/context regions, crop link),
  warnings/limitations
- overlays/crops: `<out>/pages/page_NNN_overlay.png`, `<out>/crops/<kind>_<index>_body.png`
- `summary.json`: `{ok, pdf, pages, figures_detected, tables_detected,
  common_regions_detected, watermarks_detected, artifacts{manifest, review_index,
  pages, crops}, warnings}`

## 5. RTM regression check
- rtm_frozen compare: cases 47/49, objects 100/100, missing 0, extra 0, regions
  206/210 — **identical to D16.5 (no regression)**
- pytest: **136 passed** (130 prior + 6 D17)

## 6. Real PDF smoke result
- PDF used: `dp_sample.pdf` (local VESA DisplayPort spec excerpt — NOT committed)
  - pages: 6
  - figures detected: 3
  - tables detected: 3
  - common regions: 43 (incl. 3 watermarks — the diagonal "Licensed to …" mark)
  - warnings: none
  - artifact path: `artifacts/real_pdf_smoke/dp_sample/` (git-ignored)
- second sample `dp_sample1.pdf` (2 pages): 0 figures / 0 tables → emits the
  "no figures or tables detected" warning (no crash, structured result).

## 7. Did not touch
- rtm_frozen: unchanged
- RTM scenarios: unchanged
- truth schema: unchanged
- compare tolerance: unchanged
- detector: unchanged (no real-PDF case-specific hardcoding)

## 8. Known limitations
- no ground truth for real PDF: output is a visual review package only; no pass/fail,
  no correctness claim. An operator must confirm each figure/table band.
- rotated/morph/image-like watermark: extracts unreliably; reported, never silently
  skipped (carried over from D16/D16.5).
- semantic interpretation: structure/geometry (x/y-bands) only; no semantic fields.

## 9. Tests (synthetic PDF only; no user PDF committed as a fixture)
1. manifest created  2. review_index.md created  3. overlay PNG created
4. body crop created for ≥1 figure/table  5. `--json` is pure JSON
6. invalid PDF path → structured error (`INVALID_PDF_INPUT`, exit 2)
7. detector-output-v0 validator PASS  8. no truth input required

Commit on `picker-cmc-d03`. Stopping after D17 report per instruction.
