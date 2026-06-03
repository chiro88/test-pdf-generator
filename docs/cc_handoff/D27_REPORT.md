[D27 downstream object package export report]

A standard `downstream-package-v0` exported from the edited `editor-save-manifest-v0`
for downstream waveform/diagram/table LLM tools: per-object caption/body/context
crops + metadata JSON + JSONL + index. Geometry/crops only — no content
interpretation, no LLM calls. Detector and contracts untouched.

## 1. Summary
- package schema: `downstream-package-v0` (objects with regions, crops, structural
  task hint).
- CLI: `tools/export_downstream_package.py` (`--manifest`, `--out`, `--json`).
- web integration: **Export package** button → `POST /api/export/downstream`.

## 2. Files changed
- `picker_cmc_v1/downstream_package/` (NEW): `schema.py`, `validator.py`,
  `exporter.py`, `__init__.py`.
- `picker_cmc_v1/tools/export_downstream_package.py` (NEW).
- `picker_cmc_v1/web_editor/server.py`: `POST /api/export/downstream`.
- `picker_cmc_v1/web_editor/static/{index.html,app.js}`: Export package button.
- `docs/product/DOWNSTREAM_PACKAGE_V0.md` (NEW).
- `tests/test_downstream_package_d27.py` (7 functions / 10 checks).
- detector / setup schema / editor-manifest schema / rtm_frozen / tolerance: untouched.

## 3. Commands run
- `python tools/export_downstream_package.py --manifest <editor_save_manifest.json> --out <dir>/downstream_package --json`
- `python -m pytest tests picker_cmc_v1 -q` → **243 passed**; RTM regression unchanged.

## 4. Package contract
- manifest: `package_manifest.json` (`downstream-package-v0`) — `source_pdf`,
  `source_editor_manifest`, PDF-pt/top-left, `objects[]`.
- objects.jsonl: one object per line (stream-friendly), mirrors `objects`.
- crops: `crops/<figure|table>_<index>_<caption|body|context>.png`.
- task hints: structural routing only — figure → `diagram_or_waveform`,
  table → `table` (NOT semantic).

## 5. Export behavior
- source manifest: the **editor-save-manifest-v0** is the source of truth.
- edited bbox usage: crops + region fields are cut from the human-edited bboxes
  (verified: a figure body edited to `[110,108,490,210]` exports that bbox + crop).
- figure/table handling: both export caption/body/context crops + metadata; the
  validator enforces required fields.

## 6. Validation
- tests (7 fns / 10 checks): build package; package validator pass; objects.jsonl;
  figure + table caption/body/context crops; crop uses edited bbox; invalid manifest
  rejected; CLI `--json` pure; web `/api/export/downstream` builds the package; RTM
  frozen unchanged.
- sample package: synthetic PDF (1 figure + 1 table) → 2 objects, 6 crops,
  validator PASS, figure body == edited bbox, hints `diagram_or_waveform` / `table`.
- sample paths: `downstream_package/{package_manifest.json, objects.jsonl, index.md, crops/*.png}`.

## 7. Did not touch
- detector: unchanged
- setup schema: unchanged
- editor manifest schema: unchanged
- rtm_frozen: unchanged
- compare tolerance: unchanged

## 8. Known limitations
- no semantic interpretation (waveform/table content not parsed)
- no LLM call (the package is the hand-off; interpretation is downstream)
- crops are raster at a fixed scale (3.0)

Commit on `picker-cmc-d03`. Stopping after D27 report.
