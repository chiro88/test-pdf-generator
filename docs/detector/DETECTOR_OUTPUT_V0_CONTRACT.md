# detector-output-v0 contract

The manifest a picker_cmc detector emits and the RTM compare harness consumes.
Defined in `picker_cmc_v1/detector_output/` (`schema.py`, `validator.py`,
`writer.py`). `writer.write_manifest()` refuses to write an invalid manifest.

## Top level

```json
{
  "schema_version": "detector-output-v0",
  "coordinate_unit": "pdf_pt",
  "coordinate_origin": "top-left",
  "producer": { "name": "picker_cmc", "version": "dev", "mode": "detector" },
  "cases": [ { "case_id": "...", "pdf": "...", "pages": [ ... ] } ]
}
```

- Coordinates are **PDF points**, **top-left** origin: bbox = `[x0, y0, x1, y1]`,
  y increasing downward. No bottom-left flip anywhere.
- `producer.mode` is `detector` for a real run; the synthetic contract test uses a
  different mode and makes no correctness claim.

## Page

```json
{ "page": 1, "common_regions": [ ... ], "figures": [ ... ], "tables": [ ... ] }
```

## Figure

```json
{
  "kind": "figure", "index": "3-3", "title": "Read transfer ...",
  "caption_region": [x0,y0,x1,y1],
  "body_region":    [x0,y0,x1,y1],
  "context_region": [x0,y0,x1,y1],
  "title_position": "below",          // "above" | "below"
  "title_body_gap_lines": 0
}
```

## Table

```json
{
  "kind": "table", "index": "3-1", "title": "Transfer type encoding",
  "table_group_id": "tbl_003_001", "part_index": 1,
  "is_continuation": false, "continuation_marker": null,
  "caption_region": [...], "body_region": [...],
  "context_region": [...],                 // optional
  "continued_from": null                    // group id when is_continuation
}
```

`table_group_id` is canonical (`tbl_<NNN>_<MMM>`); continuation parts share the
group id and increment `part_index`.

## Common region

```json
{ "kind": "header"|"footer"|"watermark", "bbox": [x0,y0,x1,y1],
  "text": "...", "common_region_id": "hdr_001" }   // text/id optional
```

## Validation

`validator.validate_manifest(data)` returns a list of contract violations (empty =
valid); `validate_or_raise` raises `DetectorOutputError`. It checks structure only —
**not** detector correctness. The compare harness then matches detected vs truth
objects by identity key (page+kind+ordinal / table group+part) with per-axis
tolerance.

## Stability

`detector-output-v0` is the integration contract for the RTM compare harness, the
real-PDF review harness, and the upcoming web editor. Treat it as frozen for v0:
extend with new optional fields rather than changing existing ones.
