[D26 setup YAML web workflow + run launcher report]

The browser entry flow: download a setup template, validate it, run the detector,
and open the generated run in the editor. Local single-user; no auth/DB/cloud. The
D23-D25 viewer/edit/export behavior is unchanged; the detector is untouched.

## 1. Summary
- setup web workflow: template / validate / run endpoints + a left-pane setup panel.
- run launcher: the server holds a Workspace of runs (one current); `POST
  /api/setup/run` creates a run and opens it; `GET /api/runs` / `GET /api/run/{id}`
  list and open.
- viewer integration: all D23-D25 viewer/edit/export APIs operate on the current
  run; before any run is open they return `NO_RUN_OPEN`.

## 2. Files changed
- `picker_cmc_v1/web_editor/workflow.py` (NEW): `parse_setup` (path or inline YAML),
  `run_from_setup` (validate + detect + write manifests).
- `picker_cmc_v1/web_editor/models.py`: `Workspace` (runs_root, current, register/
  open/list_runs).
- `picker_cmc_v1/web_editor/server.py`: workspace-based handler; setup/runs endpoints;
  `make_server` accepts a Workspace OR a RunContext (backward compatible).
- `picker_cmc_v1/tools/run_web_editor.py`: builds a Workspace.
- `picker_cmc_v1/web_editor/static/{index.html,app.js,styles.css}`: setup panel +
  runs list.
- `docs/product/WEB_EDITOR_V0.md`: D26 section.
- `tests/test_web_editor_setup_workflow_d26.py` (9).
- detector / setup schema / editor-manifest schema / rtm_frozen / tolerance: untouched.

## 3. Commands run
- `python tools/run_web_editor.py --run-dir <dir>` (setup panel reachable in browser)
- `python -m pytest tests picker_cmc_v1 -q` → **236 passed**; RTM regression unchanged.

## 4. API changes
- template: `GET /api/setup/template` → commented `setup-yaml-v0` text.
- validate: `POST /api/setup/validate {setup_yaml|setup_path}` → `{ok}` or structured
  setup error (`SETUP_MISSING_FIELD`, `SETUP_PLACEHOLDER_UNRESOLVED`, …).
- run: `POST /api/setup/run` → validate + detect + write manifests → `{ok, run_id,
  run_dir, page_count}` and sets it current.
- run list/open: `GET /api/runs`; `GET /api/run/{run_id}` (run_id = directory name).

## 5. UI behavior
- setup panel: Download template → textarea; Validate; Run detector; runs list.
- validation errors: shown inline (code + field) as JSON-backed messages.
- open editor: a successful run (or a runs-list click) loads the page viewer,
  object tree, and overlays.
- existing edit/save/export: unchanged — they act on the current run.

## 6. Validation
- tests (9): template text; validate ok; invalid setup (`SETUP_MISSING_FIELD`);
  placeholder (`SETUP_PLACEHOLDER_UNRESOLVED`); setup run creates manifests; created
  run opens in viewer APIs + runs list + `/api/run/{id}`; `NO_RUN_OPEN` guard before a
  run; run-dir backward-compat (RunContext still serveable); RTM frozen unchanged.
- existing D23-D25 web tests: 29 still pass (workspace wraps a RunContext).
- sample setup run: a synthetic PDF setup → `run1` with `detected_manifest.json` +
  `editor_save_manifest.json`, opened via the viewer APIs.

## 7. Did not touch
- detector: unchanged
- setup schema: unchanged (no new required fields; optional UI use only)
- editor manifest schema: unchanged
- rtm_frozen: unchanged
- compare tolerance: unchanged

## 8. Known limitations
- local single-user only (one current run in memory)
- no auth
- no database (file-backed runs)
- no cloud upload

Commit on `picker-cmc-d03`. Stopping after D26 report.
