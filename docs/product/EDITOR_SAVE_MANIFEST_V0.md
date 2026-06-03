# editor-save-manifest-v0

The web editor's final saved artifact: a **human-corrected candidate** derived from
the detector's initial proposal. Implemented in `picker_cmc_v1/editor_manifest/`.

## Principles

- The detector output is an **initial proposal**, not a final answer.
- The save manifest is the **human-corrected final candidate**.
- Keep an **append-only edit log** — do not leave only an in-place mutation.
- Coordinates stay **PDF points, top-left origin**.

## Shape

```json
{
  "schema_version": "editor-save-manifest-v0",
  "source_pdf": "...",
  "source_detector_manifest": "...",
  "coordinate_unit": "pdf_pt",
  "coordinate_origin": "top-left",
  "pages": [
    { "page": 1, "figures": [ ... ], "tables": [ ... ], "common_regions": [ ... ] }
  ],
  "edits": [
    {
      "object_id": "figure:3-3:page1",
      "operation": "update_bbox",
      "region": "body_region",
      "before": [10, 10, 20, 20],
      "after":  [11, 12, 33, 44]
    }
  ]
}
```

`pages[]` carries the current (post-edit) object state — the same object shapes as
`detector-output-v0`. `edits[]` is the audit log of operator actions.

## Operations

| operation | meaning |
|---|---|
| `update_bbox` | move/resize a `region` of an existing object (`caption_region` / `body_region` / `context_region` / `bbox`) |
| `update_field` | change a non-region field (title, index, …) |
| `add_object` | operator added a missed figure/table |
| `remove_object` | operator removed a false-positive object |

## Build + edit (programmatic)

```python
from editor_manifest import writer
save = writer.build_initial(detector_manifest, source_pdf="in.pdf",
                            source_detector_manifest="detected_manifest.json")
writer.apply_bbox_edit(save, "figure:3-3:page1", "body_region", [11, 12, 33, 44])
writer.write_manifest("editor_save_manifest.json", save)   # validates on write
```

`build_initial` pre-loads the proposal with an empty edit log; `apply_bbox_edit`
updates the region in place AND appends the edit.

## Validate

```bash
python tools/validate_editor_manifest.py --manifest editor_save_manifest.json --json
```

`validator.validate_manifest` rejects a wrong `coordinate_unit`/`coordinate_origin`,
a missing `source_pdf`/`source_detector_manifest`, malformed pages, or a malformed
edit (unknown operation, non-bbox `after`). Structure only — not a correctness judge.
