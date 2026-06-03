# Troubleshooting

Common issues running picker_cmc v0. Most are setup/path problems, not code bugs.

## Install / import

| symptom | fix |
|---|---|
| `ModuleNotFoundError: fitz` | `pip install -r requirements.txt` (PyMuPDF provides `fitz`) |
| `ModuleNotFoundError: yaml` | `pip install PyYAML` |
| `ModuleNotFoundError: detector` / `setup` / `web_editor` | run tools from `picker_cmc_v1/` (the tools add it to `sys.path`); run `pytest` from the repo root |

## Setup YAML errors (structured codes)

| error_code | meaning / fix |
|---|---|
| `SETUP_FILE_NOT_FOUND` | the `--setup` path doesn't exist |
| `SETUP_FILE_UNREADABLE` | not valid YAML / not a mapping |
| `SETUP_MISSING_FIELD` | a required field is absent (e.g. `input.pdf_path`) |
| `SETUP_PLACEHOLDER_UNRESOLVED` | a `CHANGE_ME` was left in — fill `project.name` / `input.pdf_path` |
| `SETUP_INVALID_VALUE` | a field is present but wrong (e.g. bad `input.pdf_path`) |
| `SETUP_BAD_PAGE_RANGE` | `input.page_range` malformed (use `"1-5"` or `"3"`) |
| `SETUP_UNKNOWN_DETECTOR` | `advanced_fine_tuning.detector_profile` must be `default` |

## Web editor

| symptom | fix |
|---|---|
| viewer shows "no run open" | use the setup panel (Run detector) or `GET /api/run/{run_id}`; the CLI `--run-dir`/`--setup` opens one at start |
| `NO_RUN_OPEN` (409) from an API | open a run first (setup panel / `--run-dir`) |
| page image blank / `cannot render page` | the run's `source_pdf` path must still resolve on this machine |
| `SAVE_PATH_NOT_ALLOWED` on Save-As | Save-As targets must be inside the run directory |
| `MANIFEST_OUTSIDE_RUN_DIR` on `--manifest` | the explicit manifest must live inside the run directory |
| port already in use | pass a different `--port` |

## Edit / export

| error_code | fix |
|---|---|
| `EDIT_OBJECT_NOT_FOUND` / `EDIT_REGION_NOT_FOUND` | check the `object_id` / region name |
| `EDIT_BAD_BBOX` | bbox needs `x0<x1` and `y0<y1` |
| `EDIT_OUT_OF_PAGE_BOUNDS` | bbox must stay within the page |
| downstream export: `source_editor_manifest must be an editor-save-manifest` | export from `editor_save_manifest.json`, not `detected_manifest.json` |
| downstream export: `input must be editor-save-manifest-v0` | you passed a detector-output manifest; pass the editor manifest |

## Detector / RTM

| symptom | note |
|---|---|
| RTM shows `regions_failed: 4` | expected — the rotated/morph/image-like watermark limitation (2 cases). Not a regression. |
| real-PDF body looks off | a real PDF has no ground truth; use the operator review/edit flow to correct it. |

## "It ran but the result looks wrong"

The detector output is an **initial proposal**. Correct it in the web editor (Edit
bbox → Save), then export — the edited manifest is the source of truth.
