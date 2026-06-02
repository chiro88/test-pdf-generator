# RTM Factory — Operations Guide

The **Real Tracking Mock (RTM) factory** deterministically generates candidate
PDFs plus ground-truth JSON, previews, a gallery manifest, and a human-review
index for the `pdf-yband-picker` / `picker_cmc` detector. It then supports
promoting human-approved cases to a frozen golden set and comparing detector
output against that truth.

> **pytest green != detector correctness.** The factory and its pytest gates
> only prove the generated PDFs/truth/previews are internally valid and that the
> promotion/compare/overlay pipeline is reproducible. Detector acceptance
> requires a real detector compared against a human-approved frozen set within
> tolerance.

## Where things live

```
picker_cmc_v1/tests/fixtures/rtm_factory/
  rtm_cli.py                 # unified CLI entrypoint (agents use this)
  generate.py                # legacy: full gallery generation
  promote_keep_cases.py      # legacy: frozen promotion
  compare_detector_to_truth.py  # legacy: detector-vs-truth compare
  render_compare_artifacts.py   # legacy: overlay rendering
  rtm_factory/
    models.py scenario_specs.py layout.py templates.py
    builders/                # header_footer / watermark / figure / table / negative
    render.py truth.py gallery.py self_check.py coverage.py
    promote.py compare.py overlay.py
    cli.py errors.py scenario_io.py

picker_cmc_v1/tests/fixtures/rtm_gallery/   # generated candidates (gitignored, regenerable)
picker_cmc_v1/tests/fixtures/rtm_frozen/    # human-reviewed golden fixtures (commit-eligible; empty until Gate B)
```

## rtm_gallery vs rtm_frozen

| | rtm_gallery | rtm_frozen |
|---|---|---|
| content | generated candidates | human-reviewed accepted fixtures |
| how produced | `generate` | `promote` (copy-only) of kept cases |
| stability | regenerated every run (gitignored) | durable golden source for the detector |
| used for | development / self-check | the detector golden comparison gate |

`compare`/`overlay` accept either as `--truth-root`, but **rtm_gallery is
development-only** (a stderr warning is printed); the real gate is **rtm_frozen**.

## Command reference (use `rtm_cli.py`)

All commands accept `--json` (machine-readable single JSON object on stdout).

```bash
cd picker_cmc_v1/tests/fixtures/rtm_factory

# 1. Generate the full candidate gallery (50 cases) + run self-check
python rtm_cli.py generate --out ../rtm_gallery --json

# 2. Generate one case (built-in scenario, or a YAML/JSON scenario file)
python rtm_cli.py generate-case --case-id core_figure_caption_bottom --out artifacts/rtm_case --json
python rtm_cli.py generate-case --scenario-file my_case.yaml --out artifacts/rtm_case --json

# 3. Discover what exists
python rtm_cli.py list-scenarios --json
python rtm_cli.py list-templates --json

# 4. Validate a scenario file before generating
python rtm_cli.py validate-scenario my_case.yaml --json

# 5. Self-check a gallery (coverage gate + text-extraction overlap gate)
python rtm_cli.py self-check --gallery ../rtm_gallery --json

# 6. Promote human-kept cases (index.md keep/drop column) to a frozen set
python rtm_cli.py promote --gallery ../rtm_gallery --out ../rtm_frozen --json

# 7. Compare a detector output manifest against the frozen truth
python rtm_cli.py compare --truth-root ../rtm_frozen --detected detected.json --out artifacts/rtm_compare --json

# 8. Render review overlays from a compare report
python rtm_cli.py overlay --truth-root ../rtm_frozen --detected detected.json \
  --compare-report artifacts/rtm_compare/compare_report.json --out artifacts/rtm_overlay --json
```

Exit codes: `0` success · `1` validation/comparison failed · `2` invalid input/schema · `3` internal generation/rendering failure.

## Self-check gates (what `self-check` / `generate` enforce)

- **Coordinate contract**: every bbox is `[x0,y0,x1,y1]`, origin top-left, y down, unit `pdf_pt`.
- **Truth enum**: `kind ∈ {figure, table, header, footer, watermark}`; figures/tables use `caption_region` / `body_region` / `context_region`.
- **Coverage gate**: each required axis value appears ≥2 (or ≥1 with a justification in `MANIFEST.coverage_summary.exceptions`); `missing`/`below_min` must be empty.
- **Presence**: 8 core + 6 negative scenarios by exact name; all 5 continuation suffixes; `A.1` alpha index in ≥2 cases; a diagonal watermark present.
- **Text-extraction overlap**: every text region (header/footer/upright watermark/figure+table caption) must overlap real `get_text("dict")` text whose content contains the expected key. Rotated/morph watermarks are skipped **with a recorded reason** in `SELF_CHECK_REPORT.json`.

## Pipeline order

```
generate  ->  human Gate B review (index.md)  ->  promote  ->  rtm_frozen
                                                                   |
detector output manifest (detector-output-v0) --> compare --> overlay (review)
```

Detector integration is a later milestone; today rtm_frozen is empty and the
detector does not exist in this tree.
