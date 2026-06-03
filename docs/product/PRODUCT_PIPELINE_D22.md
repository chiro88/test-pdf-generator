# Product pipeline (D22 contract foundation)

The contract layer the web editor / server will sit on. D22 fixes the **contracts**
(setup YAML in, save manifest out) and the detector adapter — **not** the web UI or
server.

```
setup-yaml-v0  (user input: PDF + document hints + output paths)
   │  tools/run_detector_with_setup.py
   ▼
detector-output-v0  (initial PROPOSAL — figures/tables/common-regions, PDF-pt top-left)
   │  build_initial()
   ▼
editor-save-manifest-v0  (human-corrected final candidate + append-only edit log)
   ▲  apply_bbox_edit() / future web editor
   │
operator review (overlays/crops + review_index; real-pdf-review-v0 feedback)
```

## Layers

| layer | contract | module | doc |
|---|---|---|---|
| input | `setup-yaml-v0` | `setup/` | `SETUP_YAML_V0.md` |
| detector output | `detector-output-v0` | `detector_output/` | `../detector/DETECTOR_OUTPUT_V0_CONTRACT.md` |
| saved output | `editor-save-manifest-v0` | `editor_manifest/` | `EDITOR_SAVE_MANIFEST_V0.md` |
| review feedback | `real-pdf-review-v0` | `detector/review_feedback.py` | `../detector/REAL_PDF_REVIEW_WORKFLOW.md` |

## CLIs (D22)

```bash
python tools/make_setup_template.py     --out setup.yaml
python tools/run_detector_with_setup.py --setup setup.yaml --json
python tools/validate_editor_manifest.py --manifest editor_save_manifest.json --json
```

## Coordinate invariant

Every layer is **PDF points, top-left origin** (`[x0, y0, x1, y1]`, y down). No
axis flip anywhere; the web editor renders these directly over the page raster.

## Roundtrip guarantee

`detector-output-v0 → build_initial → editor-save-manifest-v0` preserves every
object (figures/tables/common-regions) verbatim as the starting proposal; operator
edits only ever add to `pages[]` state + the `edits[]` log. A saved manifest always
validates before being written.

## What D22 does NOT include

- No web UI, no server.
- No detector algorithm change, no RTM/truth/tolerance change.
- `document_hints` is carried but advisory for v0 (the detector is already robust);
  it is the forward-compatible slot for future per-document tuning.

## Next milestone

Web editor / server that renders `detected_manifest.json`, lets an operator edit
regions, and saves an `editor-save-manifest-v0` (see `../detector/WEB_EDITOR_HANDOFF.md`).
