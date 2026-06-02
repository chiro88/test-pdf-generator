# RTM Factory — Milestone Closeout (D2 → D7)

Status: **RTM factory feature-complete; awaiting Gate B human review.**
The detector does not exist in this tree and is intentionally not integrated.

## What was built (per stage)

| Stage | Commit | Outcome |
|---|---|---|
| D2 | `18fe638` | Scenario expansion 19→42; structural coverage taxonomy + coverage-gating self-check |
| D3 | `524c3a5` | Frozen promotion (`promote_keep_cases.py`): index.md keep/drop → `rtm_frozen`, copy-only, fail-safe |
| D3.5 | `691656c` | Truth-region vs `get_text("dict")` overlap gate (caught 2 real non-rendering bugs); frozen gitignore policy |
| D4 | `2f33222` | Detector-vs-truth compare harness: identity-key matching, per-axis tolerance, JSON+md report, exit 0/1/2 |
| D5 | `53bbaa2` | Overlay/diff artifacts: truth/detected/failure/missing/extra visualization, failures-only default |
| D5.5 | `3051c59` | Unified LLM-friendly CLI (`rtm_cli.py`) with `--json`, structured error codes, exit codes |
| D6 | `c295f2e` | pytest full integration gate + argparse-JSON + seed provenance; markers `slow`/`rtm_integration` |
| D7 | `3e99073` | Common-region realism: structural diversity + deterministic per-page jitter; 42→50 cases |

## Current corpus

- **50 candidate cases**: 8 core, 6 negative, 36 expanded (within the 30–50 gate).
- Per case: PDF + `truth.json` + page preview PNG(s) + `notes.md`.
- `MANIFEST.json` carries a machine-readable `coverage_summary` (counts / required / missing / below_min / exceptions) and `generation.seed`.

## Coverage axes (summary)

- **page**: size (letter/a4), orientation, columns, pages (1/3/8), offset
- **header/footer**: mode (none/header_only/footer_only/both), variable page-number/subtitle, mirrored, rule_line, partial; **D7**: rule (none/header/footer/both), page-number position (bottom_center/bottom_right/page_x_of_y), subtitle position (centered/top_right), support (all_pages/first_page_suppressed/partial), jitter (xy/rule_y/evenodd)
- **watermark**: presence, location, opacity, rotation, image_like; **D7**: jitter (position/rotation_opacity/variable_text/near_footer)
- **figure**: caption pos, alias, index style, title lines, body kind, width, multiplicity
- **table**: span, parts, suffix variants, title repeat, fragment, width, caption pos
- **negative**: 6 named scenarios

Self-check result on the current corpus: `missing=[]`, `below_min=[]`,
text-overlap `118/118 matched`, `8 skipped` (rotated/morph watermarks, reasons recorded).

## Quality gates in place

- coverage gate (≥2 per axis value, or ≥1 with justification)
- exact core/negative name presence; all continuation suffixes; A.1 ≥2; diagonal watermark present
- text-extraction overlap gate (uses each page's **actual** bbox, jitter-aware)
- compare harness with strict-by-default pass/fail and per-axis tolerance
- pytest integration: `python -m pytest tests -q` → 45 passed; `-m "not slow"` 32; `-m rtm_integration` 8

## Known limitations

- `rtm_frozen` durable set is **empty** until Gate B human review.
- Jitter is deterministic (page-indexed), not random; statistical/group bbox is out of scope (a detector may derive it later — RTM truth/compare/overlay stay per-page).
- Multi-part common regions match by `(page, kind, ordinal)`; a future detector providing text-normalized keys would warrant a secondary matching aid.
- `thick_bar_or_double_rule` rule variant not generated (excluded from required values).
- Some D7 jitter stress axis values are min1 (single representative); can be expanded to min2 if the detector proves weak there.

## Prerequisites before detector integration

1. **Gate B** completed: human-reviewed `rtm_frozen` exists (see the review protocol).
2. A detector emitting a `detector-output-v0` manifest (`coordinate_unit=pdf_pt`, `coordinate_origin=top-left`).
3. `compare` run against `rtm_frozen` (not `rtm_gallery`) producing 0 failures within tolerance, with `overlay` artifacts for any mismatch.

Until those hold, **pytest green is a factory-reproducibility signal only, not detector acceptance.**
