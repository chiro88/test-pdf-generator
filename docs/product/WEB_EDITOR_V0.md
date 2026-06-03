# Web editor v0 — read-only foundation (D23)

A local, dependency-light viewer for a detector run: it renders pages, shows the
figure/table/common-region tree, draws bbox overlays, and lets you navigate by
clicking an object. **Read-only** — no bbox editing, no save, no ruler (those are
D24). Built on the Python stdlib `http.server` (no new dependencies).

## Launch

```bash
# from picker_cmc_v1/

# (a) serve an existing run directory (D22 output)
python tools/run_web_editor.py --run-dir artifacts/picker_run --host 127.0.0.1 --port 8765

# (b) from a setup YAML — creates the run, then serves
python tools/run_web_editor.py --setup setup.yaml --host 127.0.0.1 --port 8765
```

`--setup` mode reuses the D22 flow: it writes `detected_manifest.json` and
`editor_save_manifest.json` under the setup's `output.artifact_dir`, then serves.

The run is loaded into a `RunContext`; an `editor-save-manifest-v0` is **validated
before the server starts** (an invalid manifest is a structured load error).

## API

| endpoint | returns |
|---|---|
| `GET /` | static `index.html` |
| `GET /static/app.js`, `/static/styles.css` | static assets |
| `GET /api/health` | `{ok, status}` |
| `GET /api/run` | `web-editor-run-v0` (source_pdf, manifest, page_count, coords) |
| `GET /api/manifest` | the editor-save-manifest-v0 |
| `GET /api/pages` | `{pages: [1, 2, …]}` |
| `GET /api/page/{page}/png?scale=1.5` | rendered page PNG |
| `GET /api/page/{page}/objects` | `{page, figures[], tables[], common_regions[]}` (each with `object_id`) |
| `GET /api/page/{page}/overlays` | `{page, overlays:[{object_id, kind, region, bbox}]}` |
| `GET /api/object/{object_id}` | `{object_id, page, kind, object}` |

`/api/run` shape:

```json
{ "ok": true, "schema_version": "web-editor-run-v0", "source_pdf": "...",
  "manifest": "...", "page_count": 6, "coordinate_unit": "pdf_pt",
  "coordinate_origin": "top-left" }
```

`object_id` is `"<figure|table>:<index>:page<N>"`; common regions use
`"common:<id>:page<N>"`.

## Viewer

- **Left pane**: Figures / Tables / Common-regions trees (page-tagged); click an
  object to select it.
- **Right pane**: rendered page image with bbox overlays; the selected box is
  highlighted; page prev/next.
- **Top toolbar**: toggle Figures / Tables / Header / Footer / Watermark / all.
  Edit-bbox / Ruler / Save buttons are present but **disabled with a "D24" note**.

## Coordinate handling

Bboxes are PDF points, top-left origin. The page is rendered at a fixed `scale`
(1.5); overlays are positioned at `bbox * scale`. No axis flip.

## Editing (D24)

Switch the top toolbar to **Edit bbox** mode, select an object (tree or overlay),
pick a region (`caption_region` / `body_region` / `context_region`, or `bbox` for a
common region), then **drag to move** or use the **corner/edge handles to resize**.
The live `[x0, y0, x1, y1]` (PDF pt, top-left) is shown in the readout bar. Each
commit calls the API and appends to the manifest edit log; an **unsaved** badge
tracks dirty state.

### Edit / save API

| endpoint | body / effect |
|---|---|
| `POST /api/edit/bbox` | `{object_id, region, bbox}` → `{ok, before, after, dirty}`; updates in memory + appends edit log |
| `POST /api/save` | overwrite the run's `editor_save_manifest.json` (validate first) |
| `POST /api/save-as` | `{path}` → write under the run dir (path-traversal rejected) |
| `GET /api/edit-state` | `{dirty, edit_count, save_path}` |

Edit validation (structured error `{ok:false, error_code, message, field}`):
`EDIT_OBJECT_NOT_FOUND`, `EDIT_REGION_NOT_FOUND`, `EDIT_BAD_BBOX` (requires
`x0<x1`, `y0<y1`), `EDIT_OUT_OF_PAGE_BOUNDS`, `SAVE_MANIFEST_INVALID`,
`SAVE_PATH_NOT_ALLOWED`, `SAVE_WRITE_FAILED`.

The manifest is **validated before every write**; edits are an append-only log, and
Save-As preserves the original file. Coordinates stay PDF-pt / top-left
(`screen_px → pdf_pt = px / scale`, no y-flip).

### Ruler (D24, client-side only)

Switch to **Ruler** mode: first click = start, second click = end. The readout
shows start/end (PDF pt), `dx`, `dy`, and straight-line distance. Ruler data is
**never persisted** to the manifest.

## Not yet (later milestones)

- multi-user / sessions, job queue, database
- advanced setup UI
