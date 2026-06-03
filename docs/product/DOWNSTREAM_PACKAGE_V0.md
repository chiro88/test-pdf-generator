# downstream-package-v0

A standard, geometry-only object package for downstream waveform/diagram/table LLM
tools. Built from the **edited** `editor-save-manifest-v0`, it carries the
human-corrected bboxes + per-object crops. It does **not** interpret content and
makes no LLM calls. Implemented in `picker_cmc_v1/downstream_package/`.

## Build

```bash
python tools/export_downstream_package.py \
    --manifest artifacts/picker_run/editor_save_manifest.json \
    --out artifacts/picker_run/downstream_package --json
```

Or from the web editor: **Export package** (`POST /api/export/downstream`) writes
the package under the current run dir.

## Output

```
downstream_package/
  package_manifest.json     # downstream-package-v0
  objects.jsonl             # one object per line (stream-friendly)
  index.md                  # human overview
  crops/
    figure_3-5_caption.png
    figure_3-5_body.png
    figure_3-5_context.png
    table_3-1_body.png      # (+ caption/context)
```

## Schema

```json
{
  "schema_version": "downstream-package-v0",
  "source_pdf": "...",
  "source_editor_manifest": "...",
  "coordinate_unit": "pdf_pt",
  "coordinate_origin": "top-left",
  "objects": [
    {
      "object_id": "figure:3-5:page1",
      "kind": "figure",          // figure | table
      "page": 1,
      "index": "3-5",
      "title": "Multiple transfers",
      "caption_region": [x0,y0,x1,y1],
      "body_region":    [x0,y0,x1,y1],
      "context_region": [x0,y0,x1,y1],
      "crops": { "caption": "crops/...", "body": "crops/...", "context": "crops/..." },
      "downstream_task_hint": "diagram_or_waveform"   // table -> "table"
    }
  ]
}
```

- Coordinates are PDF pt / top-left, taken from the **edited** manifest.
- `downstream_task_hint` is a **structural routing** hint (figure →
  `diagram_or_waveform`, table → `table`), NOT a semantic claim about the content.
- `objects.jsonl` mirrors `objects` one-per-line for streaming consumers.

## Validation

`downstream_package.validator.validate_package` checks schema/coords/source fields
and each object (id, kind, page, caption/body regions, crops, task hint). Structure
only — it does not judge correctness.

## Out of scope (D27)

- No waveform/diagram/table semantic interpretation.
- No LLM calls.
- The package is the stable hand-off; interpretation is a downstream tool's job.
