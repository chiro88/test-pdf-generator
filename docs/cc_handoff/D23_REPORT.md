[D23 web editor/server read-only foundation report]

The first runnable web-editor shell: a local read-only viewer over a detector run.
Stdlib `http.server` only (no new dependency). No bbox editing / save / ruler — those
are D24.

## 1. Summary
- server: `picker_cmc_v1/web_editor/server.py` (stdlib `ThreadingHTTPServer`); a
  `RunContext` over an `editor-save-manifest-v0` (validated before serving).
- frontend: static `index.html` / `app.js` / `styles.css` (object tree + page raster
  + bbox overlays + toggles + object-click navigation).
- API: read-only JSON/PNG endpoints (`/api/run`, `/api/pages`, `/api/page/{n}/png`,
  `/api/page/{n}/objects`, `/api/page/{n}/overlays`, `/api/object/{id}`, `/api/health`).
- run modes: `--run-dir <existing>` or `--setup <yaml>` (D22 flow then serve).

## 2. Files changed
- `picker_cmc_v1/web_editor/` (NEW): `__init__.py`, `models.py` (RunContext +
  `web-editor-run-v0` + load/validate), `page_render.py`, `manifest_view.py`,
  `server.py`, `static/{index.html,app.js,styles.css}`.
- `picker_cmc_v1/tools/run_web_editor.py` (NEW) — CLI (`--run-dir` / `--setup`,
  `--host`, `--port`).
- `docs/product/WEB_EDITOR_V0.md` (NEW).
- `tests/test_web_editor_d23.py` (9).
- detector / setup schema / editor-manifest schema / rtm_frozen / tolerance: untouched.

## 3. Commands run
- `python tools/run_web_editor.py --run-dir artifacts/picker_run --port 8765`
- `python tools/run_web_editor.py --setup setup.yaml --port 8765`
- `python -m pytest tests picker_cmc_v1 -q` → **207 passed**; RTM regression unchanged.

## 4. Web server contract
- CLI: `run_web_editor.py` (`--run-dir` OR `--setup`, `--host`, `--port`).
- endpoints: `/`, `/static/app.js`, `/static/styles.css`, `/api/health`, `/api/run`,
  `/api/manifest`, `/api/pages`, `/api/page/{n}/png?scale=`, `/api/page/{n}/objects`,
  `/api/page/{n}/overlays`, `/api/object/{object_id}`.
- static assets: served from `web_editor/static/`.
- `/api/run` returns `web-editor-run-v0` (source_pdf, manifest, page_count, coords).

## 5. Viewer behavior
- object tree: Figures / Tables / Common-regions, page-tagged, clickable.
- page rendering: `/api/page/{n}/png` (PyMuPDF, PDF-pt top-left, scale 1.5).
- overlays: bbox boxes positioned at `bbox * scale`; per-kind colors.
- selection/highlight: clicking a tree item or a box selects it (navigates to its
  page and highlights the box).
- toggles: Figures / Tables / Header / Footer / Watermark / all. Edit / Ruler / Save
  buttons present but **disabled with a "D24" note**.

## 6. Validation
- tests (9 functions, the 10 required checks): starts with run-dir; setup mode
  creates artifacts; `/api/health`; `/api/run` (pdf/manifest/page_count/coords);
  `/api/page/1/png` PNG magic bytes; `/api/page/1/objects` figures/tables/common;
  `/api/object/{id}` correct; static index/app/css; invalid run-dir →
  `RUN_DIR_NOT_FOUND`; invalid editor-save-manifest → `RUN_MANIFEST_INVALID` before
  serving.
- sample run: a synthetic 1-page PDF run serves end-to-end (health ok, run page_count,
  page PNG 11 KB, object tree populated). User real PDFs are not committed as fixtures.

## 7. Did not touch
- detector algorithm: unchanged
- setup schema: unchanged
- editor manifest schema: unchanged (read-only consumer only)
- rtm_frozen: unchanged
- compare tolerance: unchanged

## 8. Known limitations
- no drag edit yet (D24)
- no save edits yet (D24)
- no ruler yet (D24)
- single fixed render scale (1.5); zoom is browser-side only.

Commit on `picker-cmc-d03`. Stopping after D23 report.
