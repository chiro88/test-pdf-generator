# Detector milestone closeout — D11 → D20.5

This closes the no-truth detector milestone. The detector reads a PDF and emits a
`detector-output-v0` manifest (figures/tables/common-regions with caption/body/
context bands); it is validated against the frozen RTM golden set and exercised on
real PDFs through a visual operator-review harness. **No detector code or RTM asset
changes are part of D21 — this is documentation only.**

## What was built (by stage)

| stage | what landed |
|---|---|
| D11 | PyMuPDF extraction + caption title anchors + first body/caption inference |
| D12 / D12.5 | canonical `table_group_id` + continuation linking; truth-contract canonicalization |
| D13–D16 | common-region (header/footer) bands; watermark detection; multipart footer |
| D16.5 | PDF-derivable truth bbox for multipart footer + extractable license watermark |
| D17 | real-PDF smoke / operator review harness (`run_detector_on_pdf.py`) |
| D18 | real-PDF Figure/Table title patterns (no-colon ARM-style) + FP guards |
| D19 | real-PDF operator feedback schema + summary tooling (`real-pdf-review-v0`) |
| D20 | real-PDF body_region inference for unenclosed diagrams/waveforms + text tables |
| D20.5 | exclude Note/prose from figure body; keep full waveform + left labels |

## Accepted metrics (current baseline)

**RTM frozen golden set** (`picker_cmc_v1/tests/fixtures/rtm_frozen/`):
- 49 cases
- objects matched: **100/100**
- missing: **0** | extra: **0**
- regions ok: **206/210**
- residual 4 region failures = the rotated / morph / image-like **watermark
  limitation** (2 cases: `core_fixed_watermark`, `exp_wm_near_footer_rotation_opacity_jitter`)

**Real-PDF Gate C** (local samples, not committed):
- `dp_sample.pdf`: 3 figures / 3 tables
- `dp_sample1.pdf`: 3 figures / 1 table
- operator visual review after D20.5: **10/10 accept**, 0 bad_body_region

**Tests:** `pytest` → **185 passed**.

> Gate C "accept" is an operator visual judgement on two sample PDFs. It is **not**
> a correctness guarantee for all real PDFs — there is no ground truth for a real PDF.

## Detector status

- RTM-side: stable (objects 100/100; only the documented watermark limitation remains).
- real-PDF-side: anchor detection usable; body_region covers full figures/tables
  (diagrams, waveforms with left labels, table rows) and excludes Note/prose.
- truth-blind: the detector never reads `truth.json`; nothing is keyed on a PDF
  name, title, or case id.

## Companion documents

- `DETECTOR_REGRESSION_COMMANDS.md` — how to re-run RTM regression + tests.
- `REAL_PDF_REVIEW_WORKFLOW.md` — real-PDF smoke → review → next-task loop.
- `DETECTOR_OUTPUT_V0_CONTRACT.md` — the manifest contract.
- `WEB_EDITOR_HANDOFF.md` — consuming detector output as an editable proposal.

## Known limitations

- Rotated / morph / image-like **watermark** bbox is not PDF-derivable (4 RTM regions).
- **Semantic** interpretation (table cell meaning, signal semantics) is out of scope —
  geometry/structure only.
- A **real PDF** result is a visual-review proposal, never golden truth.
- A web editor must allow **manual correction**; the detector result is an **editable
  initial proposal**.

## Next product milestone

Web editor / setup-YAML / save-manifest integration (see `WEB_EDITOR_HANDOFF.md`).
Detector algorithm work is considered closed at D20.5 unless a new review pass
re-opens a specific item.
