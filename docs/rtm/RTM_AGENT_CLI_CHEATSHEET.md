# RTM Agent CLI Cheat Sheet

One entrypoint for LLMs/agents: `rtm_cli.py`. Every command supports `--json`
(stdout = exactly one JSON object; warnings go to stderr). Run from the factory dir:

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory
```

## Exit codes

| code | meaning |
|---|---|
| 0 | success |
| 1 | command ran but validation/comparison failed (e.g. compare passed=false) |
| 2 | invalid input / schema / unreadable file / argparse error |
| 3 | internal generation/rendering failure |

## Discovery

```bash
python rtm_cli.py list-scenarios --json     # -> {"ok":true,"scenarios":[{"case_id","axes","notes"},...]}
python rtm_cli.py list-templates --json     # -> {"ok":true,"templates":{"figure_body":[...],"watermark":[...],...}}
```

## Generate

```bash
python rtm_cli.py generate --out ../rtm_gallery --json
# -> {"ok":true,"command":"generate","gallery":"...","case_count":50,"seed":1234,
#     "manifest":"...","index":"...","text_overlap":{"checked":118,"passed":118,"skipped":8}}

python rtm_cli.py generate-case --case-id core_figure_caption_bottom --out artifacts/rtm_case --json
# -> {"ok":true,"command":"generate-case","case_id":"...","pdf":"...","truth":"...",
#     "previews":["...p01.png"],"notes":"...","page_count":1}

python rtm_cli.py generate-case --scenario-file my_case.yaml --out artifacts/rtm_case --json
```

## Validate a scenario file (YAML or JSON)

```bash
python rtm_cli.py validate-scenario my_case.yaml --json
# ok   -> {"ok":true,"valid":true,"case_id":"...","figures":N,"tables":M,"page_count":P}
# fail -> {"ok":false,"error_code":"SCENARIO_UNKNOWN_TEMPLATE",
#          "field":"figures[0].body_template","allowed_values":["waveform","diagram","raster","mixed"]}
```

Minimal scenario file:

```yaml
case_id: my_case
page: {size: letter, orientation: portrait, columns: 1, page_count: 1}
figures:
  - index: "3.4"
    title: Example waveform
    caption_region: [54, 492, 558, 520]
    body_region:    [54, 220, 558, 485]
    body_template: waveform     # waveform|diagram|raster|mixed
    alias: Figure               # Figure|Fig.|FIGURE
    caption_position: below     # above|below
    page: 1
```

Error codes: `SCENARIO_FILE_NOT_FOUND`, `SCENARIO_FILE_UNREADABLE`,
`SCENARIO_INVALID_VALUE`, `SCENARIO_UNKNOWN_TEMPLATE`, `SCENARIO_BAD_BBOX`,
`SCENARIO_OUT_OF_PAGE_BOUNDS`, `SCENARIO_UNSUPPORTED_PAGE_SIZE`,
`OUTPUT_DIR_EXISTS`, `INVALID_INPUT`, `SELF_CHECK_FAILED`, `PROMOTION_FAILED`,
`COMPARE_FAILED`, `PDF_GENERATION_FAILED`, `OVERLAY_FAILED`.

## Self-check

```bash
python rtm_cli.py self-check --gallery ../rtm_gallery --json
# -> {"ok":true,"passed":true,"coverage":{"total_cases":50,"missing":[],"below_min":[]},
#     "text_overlap":{"checked":118,"passed":118,"skipped":8,"failures":0}}
```

## Promote (Gate B → frozen)

```bash
python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --json
# -> {"ok":true,"selected":[...],"dropped":[...],"selection_source":"index.md","out_dir":"../rtm_frozen"}
# add --force to overwrite, --allow-empty to permit 0 keep, --keep a,b to override index.md
```

## Compare (detector vs truth)

```bash
python rtm_cli.py compare --truth-root ../rtm_frozen --detected detected.json \
  --out artifacts/rtm_compare --json
# -> {"ok":true,"passed":true|false,"summary":{...},"report_json":"...","report_md":"..."}
# exit 0 if passed, 1 if any case failed. --tolerance-profile strict|loose, --allow-extra
```

`detected.json` minimal shape (`detector-output-v0`):

```json
{
  "schema_version": "detector-output-v0",
  "coordinate_unit": "pdf_pt",
  "coordinate_origin": "top-left",
  "cases": [
    {"case_id": "core_figure_caption_bottom",
     "pages": [{"page": 1,
                "common_regions": [{"kind":"header","bbox":[48,18,564,54],"text":"..."}],
                "figures": [{"kind":"figure","index":"3.4","title":"...",
                             "caption_region":[...],"body_region":[...],"context_region":[...]}],
                "tables": []}]}
  ]
}
```

## Overlay (visual diff)

```bash
python rtm_cli.py overlay --truth-root ../rtm_frozen --detected detected.json \
  --compare-report artifacts/rtm_compare/compare_report.json --out artifacts/rtm_overlay --json
# -> {"ok":true,"pages_rendered":N,"cases":M,"manifest":"...","index":"..."}
# --failures-only (default when report has failures), --all, --case-id X, --pages 1,2, --scale 1.5
```

## Quick harness sanity (no detector yet)

Synthesize a "perfect" detected manifest from the truth to confirm the harness
end-to-end (this is a harness check, **not** detector acceptance):

```python
import json, pathlib
g = pathlib.Path("../rtm_gallery"); m = json.loads((g/"MANIFEST.json").read_text())
cases = []
for e in m["cases"]:
    t = json.loads((g/e["case_id"]/f"{e['case_id']}.truth.json").read_text())
    cases.append({"case_id": e["case_id"], "pages": [
        {"page": p["page"],
         "common_regions": [{k: r[k] for k in ("kind","bbox","text") if k in r} for r in p["common_regions"]],
         "figures": p["figures"], "tables": p["tables"]} for p in t["pages"]]})
json.dump({"schema_version":"detector-output-v0","coordinate_unit":"pdf_pt",
           "coordinate_origin":"top-left","cases":cases}, open("detected.json","w"))
```
