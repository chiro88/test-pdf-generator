# Detector regression commands

All commands run from `picker_cmc_v1/` unless noted. Substitute your Python
interpreter for `python`.

## 1. Unit + integration test suite

```bash
# from the repo root (real_tracking_mock_v1/)
python -m pytest tests picker_cmc_v1 -q
```

Current baseline: **185 passed**.

## 2. RTM frozen regression (detector vs frozen golden set)

```bash
# from picker_cmc_v1/
python tools/run_detector_on_rtm.py \
    --detector-cmd "python tools/detect_pdf.py --pdf {pdf} --out {out}" \
    --json
```

`{pdf}` / `{out}` are filled per case by the runner. Expected summary:

```json
{
  "cases_total": 49, "cases_passed": 47, "cases_failed": 2,
  "objects_expected": 100, "objects_matched": 100,
  "objects_missing": 0, "objects_extra": 0,
  "regions_checked": 210, "regions_failed": 4
}
```

- `objects_matched 100/100`, `missing 0`, `extra 0` are **hard** pass conditions.
- `regions_failed 4` are the rotated/morph/image-like **watermark** limitation
  (cases `core_fixed_watermark`, `exp_wm_near_footer_rotation_opacity_jitter`).
- Acceptance floor for future changes: objects 100/100, missing/extra 0, cases ≥ 45/49,
  regions ≥ 200/210.

Artifacts (git-ignored) land under `picker_cmc_v1/artifacts/detector_rtm/`:
`detected_manifest.json`, `compare/compare_report.{json,md}`.

## 3. Contract test (synthetic-from-truth, NOT a correctness proof)

```bash
python tools/run_detector_on_rtm.py --synthetic-from-truth --json
```

Copies truth as the detector output to validate the compare/manifest path only.

## 4. Single-PDF detector output

```bash
python tools/detect_pdf.py --pdf <file.pdf> --out <out.json>   # {"pages":[...]}
```

## 5. Watermark limitation (expected failures)

The two watermark cases above are expected to fail their watermark bbox region by
design (a rotated/morph watermark band is not PDF-derivable). Do not "fix" them by
tuning the detector or editing truth — they are the documented residual.
