# Artifact contracts summary

Every schema in the picker_cmc product flow. All coordinates are **PDF points,
top-left origin** (`[x0, y0, x1, y1]`, y increasing downward) — no axis flip anywhere.

```
setup-yaml-v0          → detector-output-v0 → editor-save-manifest-v0
                                                   ├→ edited-review-v0
                                                   └→ downstream-package-v0
web-editor-run-v0  (server run summary)        real-pdf-review-v0 (operator feedback)
```

| schema | module | role |
|---|---|---|
| `setup-yaml-v0` | `setup/` | user input: PDF + document hints + output paths |
| `detector-output-v0` | `detector_output/` | detector proposal (figures/tables/common-regions) |
| `editor-save-manifest-v0` | `editor_manifest/` | human-edited final state + append-only edit log |
| `edited-review-v0` | `web_editor/export.py` | post-edit overlays/crops summary |
| `downstream-package-v0` | `downstream_package/` | per-object crops + metadata for downstream tools |
| `real-pdf-review-v0` | `detector/review_feedback.py` | operator accept/issue feedback |
| `web-editor-run-v0` | `web_editor/` | `/api/run` server run summary |

## setup-yaml-v0
Required: `schema_version`, `project.name`, `input.pdf_path`, `output.artifact_dir`.
`document_hints` (figure/table title patterns, header/footer/watermark) is advisory.
Error codes: `SETUP_FILE_NOT_FOUND`, `SETUP_FILE_UNREADABLE`, `SETUP_MISSING_FIELD`
(absent), `SETUP_PLACEHOLDER_UNRESOLVED`, `SETUP_INVALID_VALUE` (present-but-wrong),
`SETUP_BAD_PAGE_RANGE`, `SETUP_UNKNOWN_DETECTOR`, `SETUP_UNKNOWN_TEMPLATE`.

## detector-output-v0
`{schema_version, coordinate_unit, coordinate_origin, producer, cases[{case_id, pdf,
pages[{page, common_regions[], figures[], tables[]}]}]}`. Figures/tables carry
caption/body/context regions; tables carry canonical `table_group_id` + continuation.
Validated structurally — not a correctness claim.

## editor-save-manifest-v0
`{schema_version, source_pdf, source_detector_manifest, coordinate_unit,
coordinate_origin, pages[], edits[]}`. `pages[]` = current (post-edit) object state;
`edits[]` = append-only log of `{object_id, operation, region, before, after}`.
`object_id = "<figure|table>:<index>:page<N>"` (common: `common:<id>:page<N>`).

## edited-review-v0
`summary.json` from the edited manifest: overlays + body crops drawn from the **edited**
bboxes (no detector re-run). `index.md` + `pages/*.png` + `crops/*.png`.

## downstream-package-v0
`{schema_version, source_pdf, source_editor_manifest, coordinate_unit,
coordinate_origin, objects[{object_id, kind, page, index, title, caption_region,
body_region, context_region, crops{caption,body,context}, downstream_task_hint}]}`.
`source_editor_manifest` MUST be the editor-save-manifest (never `detected_manifest.json`).
`downstream_task_hint` is a structural routing hint (figure → `diagram_or_waveform`,
table → `table`), not a semantic claim. `objects.jsonl` mirrors `objects` one-per-line.

## real-pdf-review-v0
Operator feedback: `objects[{object_id, decision, expected_change?, notes}]` +
`missed_objects[]`; `summarize` → counts + recommended next tasks.

## web-editor-run-v0
`/api/run`: `{schema_version, run_id, source_pdf, manifest, page_count,
coordinate_unit, coordinate_origin}`.

## Source-of-truth rule
The detector output is an **initial proposal**. Once an operator edits, the
**editor-save-manifest-v0** is the source of truth for review export and the
downstream package — both trace provenance to it, never to the detector output.
