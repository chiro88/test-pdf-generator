# Product quickstart (end-to-end)

The full picker_cmc flow, from a setup YAML to a downstream package. All commands run
from `picker_cmc_v1/`. User PDFs and run artifacts are not committed.

## One-shot smoke

```bash
python tools/run_product_e2e_smoke.py --pdf /path/to/input.pdf --workdir /tmp/e2e --json
```

This runs every stage and prints a per-stage pass/fail summary (setup → detector →
editor manifest → edit → save → reopen → edited review export → downstream package).

## Step by step

```bash
# 1. setup YAML
python tools/make_setup_template.py --out setup.yaml      # fill the CHANGE_ME values

# 2. run the detector from setup -> detected_manifest.json + editor_save_manifest.json
python tools/run_detector_with_setup.py --setup setup.yaml --json

# 3. open the web editor (read-only viewer + bbox edit/ruler/save)
python tools/run_web_editor.py --run-dir <artifact_dir> --host 127.0.0.1 --port 8765
#    or launch + create runs from the browser setup panel:
python tools/run_web_editor.py --setup setup.yaml --port 8765

#    In the browser: select an object, Edit bbox (drag/resize), Save / Save As.

# 4. reopen a saved (e.g. Save-As) manifest
python tools/run_web_editor.py --run-dir <artifact_dir> \
    --manifest <artifact_dir>/versions/edited.json

# 5. export post-edit review overlays/crops (from the edited manifest)
python tools/export_editor_manifest_artifacts.py \
    --manifest <artifact_dir>/editor_save_manifest.json \
    --out <artifact_dir>/edited_review --json

# 6. export the downstream object package (for downstream LLM tools)
python tools/export_downstream_package.py \
    --manifest <artifact_dir>/editor_save_manifest.json \
    --out <artifact_dir>/downstream_package --json
```

## What you get

```
<artifact_dir>/
  detected_manifest.json        detector-output-v0 (initial proposal)
  editor_save_manifest.json     editor-save-manifest-v0 (human-edited, edit log)
  edited_review/                edited-review-v0 (overlays + crops from edited bboxes)
  downstream_package/           downstream-package-v0 (per-object crops + objects.jsonl)
```

See `ARTIFACT_CONTRACTS_SUMMARY.md` for every schema, and
`PRODUCT_RELEASE_CANDIDATE_CHECKLIST.md` for the RC gate.
