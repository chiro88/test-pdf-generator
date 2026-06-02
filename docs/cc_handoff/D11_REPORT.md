# [D11 no-truth detector baseline report]

Scope: handoff D11 — a real detector that reads ONLY the PDF, emits
detector-output-v0, and whose failures are quantified by compare/overlay.

    D11 green = detector runs without truth + failures quantified
    D11 green ≠ detector correctness (0 fail is NOT the bar)

## 1. Summary
- detector modules: `pdf_extract`, `title_patterns`, `anchors`, `common_regions`, `region_inference`, `pipeline` (+ `tools/detect_pdf.py` CLI)
- frozen cases run: 49 / 49 (0 crashes)
- detector-output-v0 validation: PASS (runner validates before compare; manifest has 0 schema errors)

## 2. Files changed
- `picker_cmc_v1/detector/{__init__,models,pdf_extract,title_patterns,anchors,common_regions,region_inference,pipeline}.py` NEW
- `picker_cmc_v1/tools/detect_pdf.py` NEW (per-PDF CLI; the runner's --detector-cmd)
- `tests/test_detector_baseline_d11.py` (14) NEW
- rtm_frozen / RTM truth schema / compare tolerance / RTM scenarios: untouched

## 3. Commands run
- `python tools/run_detector_on_rtm.py --rtm-root .../rtm_frozen --out artifacts/detector_rtm --detector-cmd "python tools/detect_pdf.py --pdf {pdf} --out {out}" --json`
  → `ok=true, producer_mode=detector, case_count=49, compare_passed=false` exit 1 (baseline)
- `python -m pytest tests -q` → 73 passed

## 4. No-truth guarantee
- truth.json read by detector: **no**
- how verified:
  - `detect_pdf(pdf_path)` / `tools/detect_pdf.py --pdf --out` take only the PDF; there is no truth parameter anywhere in `detector/`.
  - test `test_detector_emits_valid_output_and_no_truth` runs the detector on a PDF with NO truth.json beside it and still gets a valid manifest.
  - the runner passes the detector a `{pdf}` (not `{truth}`); `tools/detect_pdf.py` has no `--truth` flag.

## 5. Detection results (compare vs rtm_frozen truth)
- objects expected: 100
- objects matched: 61
- missing: 39
- extra: 24
- regions checked: 117
- regions failed: 86 (31 within tolerance)
- cases passed: 5 / 49 (baseline — body/context/table-group accuracy is intentionally rough)

## 6. Anchor results (the D11 metric; truth used for EVALUATION only)
- figure anchors detected/matched: 28 / 28
- table anchors detected/matched: 25 / 25
- TOTAL anchor recall: 53 / 53 = **100%** (target ≥ 70%)
- negative false positives: **0** (Figure-of-merit / see-Table-above / "Figure 3.4 is referenced" / "Table 2.1 describes" all correctly produce NO anchor)

## 7. Compare/overlay artifacts
- detected manifest: `artifacts/detector_rtm/detected_manifest.json` (49 cases, contract-valid)
- compare report: `artifacts/detector_rtm/compare/compare_report.{json,md}`
- overlay path: `artifacts/detector_rtm/overlay/` — 63 failure pages, 126 PNGs (truth green vs detector red/orange + delta labels). Attached sample: figure+table sequence page where both anchors are found, the table body band is roughly localized, and compare flags caption-band delta + synthetic table_group_id mismatch.

## 8. Did not touch
- rtm_frozen: read-only
- truth schema: unchanged
- compare tolerance: unchanged
- RTM scenarios: unchanged

## 9. Known limitations (baseline; future detector work)
- common-region detection: header/footer hook is repeated-line based (digit-insensitive); watermark not detected; some common regions missing/extra → compare failures.
- body inference: nearest drawing-cluster heuristic; caption_region is the text-line bbox (narrower than truth's caption band) → caption deltas exceed tolerance even when the anchor is right.
- table continuation/group: `table_group_id` is synthesized per index (`det_tbl_*`) and not linked across pages, so tables mismatch truth groups (missing+extra) — continuation linking is future work.
- title-gap: title_position is inferred from body side (good), but title_body_gap_lines derives from the rough body band.

These are the failures the next detector milestone reduces — measured against
rtm_frozen 49 within the existing tolerance. No correctness is claimed here.

Commit `aa682dc` on `picker-cmc-d03` (after D10 `c6db6b6`).
Requesting D11 acceptance and the next detector-milestone target (e.g. caption-band widening, common-region accuracy, table-group linking).
