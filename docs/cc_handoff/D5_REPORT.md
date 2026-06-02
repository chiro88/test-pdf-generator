# [D5 RTM overlay/diff artifacts report]

Scope: handoff T5 / D5 only — visualize D4 compare results as review overlays.
Plus the required D4 schema_version exact-check cleanup. NOT a detector; no
detector wiring, no D6 full pytest gate, no tolerance/truth-schema changes.

## 1. Summary
- overlay harness: `rtm_factory/overlay.py` (logic) + `render_compare_artifacts.py` (thin CLI)
- tests: `tests/test_rtm_overlay_d5.py` — 6 passed
- artifacts: `artifacts/rtm_overlay/{index.md, overlay_manifest.json, <case>/page_NNN_overlay.png, page_NNN_failures.png}`

## 2. Files changed
- `rtm_factory/overlay.py`            NEW — OverlayConfig/OverlayPagePlan, collect_overlay_pages, render_pdf_page, draw_region_box, draw_object_overlay, write_overlay_manifest/_index, generate()
- `render_compare_artifacts.py`       NEW — thin CLI (truth-root/detected/compare-report/out + --case-id/--failures-only/--all/--pages/--scale)
- `tests/test_rtm_overlay_d5.py`      NEW — 6 tests
- `rtm_factory/compare.py`            D4 cleanup: schema_version must equal `detector-output-v0` exactly (was presence-only)
- `tests/test_rtm_compare_d4.py`      +1 test: wrong-version → InvalidInput
- `.gitignore`                        already ignores artifacts/
- truth schema / models.py / detector untouched

## 3. Commands run
- `python -m pytest tests/test_rtm_overlay_d5.py tests/test_rtm_compare_d4.py -q` → 18 passed; full `tests/` → 26 passed
- E2E demo: detected (one caption y+20pt) vs 42-case gallery → D4 report → `render_compare_artifacts.py` (failures-only default) rendered 1 page: overlay + failures PNG; manifest regions_drawn=6, failures_drawn=2. Visual confirm: green=truth caption, red thick=detected caption with `Δ[0,20,0,20]` label.

## 4. Input/output contract
- truth input: `--truth-root` (rtm_frozen golden / rtm_gallery dev, stderr-warned); reads `<case_id>/<case_id>.truth.json` + the case PDF for the page raster.
- detected input: `--detected` detector-output-v0 manifest (validated via compare.load_detected_manifest, now exact schema check).
- compare report input: `--compare-report` D4 compare_report.json (failures drive what is drawn).
- overlay output: `--out` dir → index.md + overlay_manifest.json (schema rtm-overlay-v0, source_* provenance, per-page overlay_png/failure_png/regions_drawn/failures_drawn) + per-page PNGs.

## 5. Visual behavior
- truth style: green solid, 2px, label prefix [H]/[F]/[WM]/[FIG idx]/[TBL group part] + region (caption/body/context).
- detected style: blue dashed, 2px.
- failure style: red thick 5px on the failing region; tolerance-fail draws truth (green) + detected (red) with `Δ[...]` delta label; field-fail draws a red label on the caption (e.g. is_continuation/continuation_marker exp/got).
- missing object: truth bbox in red. extra object: detected bbox in orange.
- failures-only behavior: when the compare report has failures, default renders only failed pages; `--all` renders every case/page; if all-pass and no `--all`, only an index ("no failures, rerun with --all") is written.
- coordinates: pt→px = bbox*scale, top-left preserved; no y flip (PyMuPDF page space is top-left, drawn directly).

## 6. Validation result
- pass/fail: PASS
- PNG checks: overlay + failure PNGs start with the PNG magic; regions_drawn>0; failure pages have failures_drawn>0.
- manifest/index checks: overlay_manifest.json schema=rtm-overlay-v0 with source_* + per-page entries; index.md created (incl. the all-pass "no failures" form). failures-only renders exactly the failed page(s); missing+extra reflected via failures_drawn>0. coordinate sanity: pt_to_px([48,18,564,54],1.5)=[72,27,846,81], within image bounds. wrong schema_version → InvalidInput.

## 7. D4 cleanup
- exact schema_version check: `load_detected_manifest` now raises InvalidInput unless schema_version == "detector-output-v0" (constant DETECTED_SCHEMA_VERSION).
- test added: `test_wrong_schema_version_is_invalid` (and overlay re-checks it via generate()).

## 8. Did not touch
- detector code: not touched (none exists)
- D6 full pytest integration: not built
- rtm_frozen durable fixtures: none committed (still awaits human Gate B; only rtm_frozen_demo/ exists, gitignored)

## 9. Known limitations
- Pixel colors are not asserted in tests (by design); structure/manifest/coords are.
- Overlay reads the page raster from the truth-root PDF; if a detector is later compared against a frozen set, the PDF must accompany the truth (it does in gallery/frozen).
- Large `--all` runs over many multipage cases can produce many PNGs; default stays failures-only to avoid artifact blowup.

Stopping after D5 as instructed. Awaiting accept/reject before D6 (pytest full integration: test_rtm_factory_generation / test_rtm_frozen_fixtures / test_rtm_detector_compare_contract).
