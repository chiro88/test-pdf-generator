# PDF Y-Band Picker RTM Factory v0

This bundle contains a deterministic **Real Tracking Mock (RTM) PDF factory** for `pdf-yband-picker` / `picker_cmc`.

It generates candidate PDFs plus ground-truth JSON, preview PNGs, notes, a gallery manifest, and a human-review `index.md`.

> **Product (v0 RC):** the detector → web editor → downstream package flow is in
> `picker_cmc_v1/`. Start with **[docs/product/OPERATOR_HANDOFF.md](docs/product/OPERATOR_HANDOFF.md)**
> (install → setup → edit → export). One-command check:
> `pip install -r requirements.txt` then
> `cd picker_cmc_v1 && python tools/run_product_e2e_smoke.py --pdf <pdf> --workdir /tmp/e2e --json`.
> See `docs/product/RC_FINAL_SIGNOFF.md` for the release gate.

## Purpose

This is not a detector correctness test by itself. It creates controlled PDF problems and their answer keys.

The detector must later be run against frozen, human-approved RTM fixtures and compared against the truth JSON.

## Command

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory
python generate.py
```

Expected output:

```text
picker_cmc_v1/tests/fixtures/rtm_gallery/
  MANIFEST.json
  index.md
  <case_id>/
    <case_id>.pdf
    <case_id>.p01.png
    <case_id>.truth.json
    <case_id>.notes.md
```

## Current v0 coverage

- 8 core cases
- 5 negative false-positive cases
- 6 expanded cases
- total: 19 candidate PDFs

This is intentionally a v0 baseline. The cc completion task is to expand it to the full RTM factory requirements: 30-50 expanded cases, frozen fixture promotion, detector-vs-truth comparison, overlay/diff artifacts, and COV mapping.

## Coordinate contract

All bboxes are:

```text
[x0, y0, x1, y1]
origin = top-left
y increases downward
unit = pdf_pt
```

## Important rule

```text
RTM factory self-check pass != detector pass
```

The factory only proves the generated PDFs, truth JSON, and previews are internally valid. Detector acceptance requires a separate golden comparison stage.
