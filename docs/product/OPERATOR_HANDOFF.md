# Operator handoff (picker_cmc v0 RC)

Run the whole picker_cmc product from a fresh checkout: install → setup → detector →
edit → export. Local single-user; no auth/DB/cloud. User PDFs and run artifacts are
never committed.

## 0. Prerequisites

- Python 3.10+ (developed on 3.12).
- Dependencies: **PyMuPDF** (`fitz`) and **PyYAML**. The web server uses only the
  Python standard library.

```bash
# from the repo root (real_tracking_mock_v1/)
python -m venv .venv && . .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
python -c "import fitz, yaml; print('deps ok')"
```

## 1. Smoke test the whole flow (one command)

```bash
cd picker_cmc_v1
python tools/run_product_e2e_smoke.py --pdf /path/to/input.pdf --workdir /tmp/picker_e2e --json
```

Every stage should print `✓` (setup → detector → editor manifest → edit → save →
reopen → edited review export → downstream package). This is the fastest "does it
work here" check.

## 2. Real operator workflow

```bash
cd picker_cmc_v1

# (a) make + fill a setup file
python tools/make_setup_template.py --out setup.yaml
#     edit setup.yaml: set project.name and input.pdf_path (remove the CHANGE_ME)

# (b) run the detector
python tools/run_detector_with_setup.py --setup setup.yaml --json
#     -> <artifact_dir>/detected_manifest.json + editor_save_manifest.json

# (c) launch the web editor and correct bboxes
python tools/run_web_editor.py --setup setup.yaml --host 127.0.0.1 --port 8765
#     open http://127.0.0.1:8765
#     - left: figure/table/common tree    - right: page + bbox overlays
#     - Edit bbox: select object -> region -> drag/resize -> Save / Save As
#     - Ruler: click start, click end -> dx/dy/distance
#     - Export package: writes the downstream package under the run dir

# (d) (optional, from the CLI) export artifacts from the saved manifest
python tools/export_editor_manifest_artifacts.py \
    --manifest <artifact_dir>/editor_save_manifest.json --out <artifact_dir>/edited_review --json
python tools/export_downstream_package.py \
    --manifest <artifact_dir>/editor_save_manifest.json --out <artifact_dir>/downstream_package --json
```

The browser **setup panel** (left pane) can also Download template / Validate / Run
detector / open runs without the CLI.

## 3. What downstream tools consume

`<artifact_dir>/downstream_package/`:
- `package_manifest.json` (`downstream-package-v0`) — objects + provenance
  (`source_editor_manifest` = the edited manifest).
- `objects.jsonl` — one object per line.
- `crops/<figure|table>_<index>_<caption|body|context>.png`.

## 4. Verify (release gate)

```bash
# from the repo root
python -m pytest tests picker_cmc_v1 -q                 # all pass
# RTM regression (from picker_cmc_v1/), see DETECTOR_REGRESSION_COMMANDS.md
python tools/run_detector_on_rtm.py \
    --detector-cmd "python tools/detect_pdf.py --pdf {pdf} --out {out}" --json
```

## Reference docs

- Quickstart: `PRODUCT_E2E_QUICKSTART.md`
- Every schema: `ARTIFACT_CONTRACTS_SUMMARY.md`
- Regression commands: `../detector/DETECTOR_REGRESSION_COMMANDS.md`
- Web editor: `WEB_EDITOR_V0.md`
- Troubleshooting: `TROUBLESHOOTING.md`
- Final sign-off: `RC_FINAL_SIGNOFF.md`

## Boundaries (v0)

- No semantic waveform/diagram/table interpretation; no LLM calls.
- Local single-user (no auth, sessions, DB, cloud, multi-user).
- Real-PDF results are operator visual-review proposals, not golden truth.
- Rotated/morph/image-like watermark bbox is a documented limitation.
