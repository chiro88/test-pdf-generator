[D24 web editor bbox edit/save/ruler report]

The minor-correction editor core: bbox edit (drag/resize), Save / Save-As to
`editor-save-manifest-v0`, and a client-side ruler. Read-only D23 behavior is
preserved; detector and contracts are untouched.

## 1. Summary
- edit mode: select object → select region → drag-move / handle-resize; live PDF-pt
  coordinate readout; every commit appends to the manifest edit log.
- save/save-as: Save overwrites the run's `editor_save_manifest.json`; Save-As writes
  a separate file under the run dir (path-traversal blocked). Both validate first.
- ruler: client-side measure (start/end click → dx/dy/distance); never persisted.

## 2. Files changed
- `picker_cmc_v1/web_editor/editing.py` (NEW): `edit_bbox`, `save`, `save_as`,
  `edit_state`, `EditError` + 7 error codes; live-object mutate + edit log.
- `picker_cmc_v1/web_editor/coords.py` (NEW): `screen_to_pdf_pt`, `ruler_measure`.
- `picker_cmc_v1/web_editor/models.py`: RunContext gains `save_path`, `page_sizes`
  (for bounds), `dirty`.
- `picker_cmc_v1/web_editor/server.py`: `do_POST` (`/api/edit/bbox`, `/api/save`,
  `/api/save-as`) + `GET /api/edit-state`.
- `picker_cmc_v1/web_editor/static/{index.html,app.js,styles.css}`: edit/ruler/save UI.
- `docs/product/WEB_EDITOR_V0.md`: D24 section.
- `tests/test_web_editor_edit_d24.py` (11 functions / the 13 required checks);
  updated one D23 static assertion.

## 3. Commands run
- `python tools/run_web_editor.py --run-dir artifacts/picker_run` (edit/save in browser)
- `python -m pytest tests picker_cmc_v1 -q` → **218 passed**; RTM regression unchanged.

## 4. API changes
- edit: `POST /api/edit/bbox {object_id, region, bbox}` → `{ok, object_id, region,
  before, after, dirty}` (or structured `EditError`).
- save: `POST /api/save` → overwrite `editor_save_manifest.json` (validate first).
- save-as: `POST /api/save-as {path}` → write under run dir; `SAVE_PATH_NOT_ALLOWED`
  on traversal.
- edit-state: `GET /api/edit-state` → `{dirty, edit_count, save_path}`.

## 5. UI behavior
- drag: move the selected region box (PDF-pt move).
- resize: 8 corner/edge handles.
- selected region: region `<select>` (caption/body/context, or bbox for common).
- coordinate display: live `[x0,y0,x1,y1]` in the readout bar (PDF pt, top-left).
- ruler: odd click = start, even = end; readout shows start/end/dx/dy/distance.

## 6. Manifest behavior
- in-memory update: the live object's region bbox is replaced (rounded to 2 dp).
- edit log: append-only `{object_id, operation:"update_bbox", region, before, after}`.
- validation: every Save/Save-As validates the editor-save-manifest before writing.
- save path policy: Save-As resolved under the run dir; outside → `SAVE_PATH_NOT_ALLOWED`.

## 7. Validation
- tests (11 functions / 13 checks): edit updates + logs before/after; invalid object/region; bbox out of
  page / x0≥x1; save writes valid manifest; save-as separate file; save-as traversal
  rejected; overlay reflects edit; page PNG still works; ruler helpers; static UI has
  D24 controls; edit-state dirty/edit_count.
- sample run: synthetic PDF — edit body_region, Save → valid manifest with edit log;
  Save-As under `versions/`; traversal blocked. (User PDFs not committed.)
- structured errors verified: EDIT_OBJECT_NOT_FOUND / EDIT_REGION_NOT_FOUND /
  EDIT_BAD_BBOX / EDIT_OUT_OF_PAGE_BOUNDS / SAVE_PATH_NOT_ALLOWED.

## 8. Did not touch
- detector: unchanged
- setup schema: unchanged
- editor-save-manifest schema: unchanged (no breaking change; edit log already in v0)
- rtm_frozen: unchanged
- compare tolerance: unchanged

## 9. Known limitations
- no multi-user / sessions (single-process, single run in memory)
- no advanced setup UI
- no database (file-backed manifest only)
- ruler is view-only (not persisted)

Commit on `picker-cmc-d03`. Stopping after D24 report.
