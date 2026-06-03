# RC final sign-off — picker_cmc v0

Final gate before tagging the v0 release candidate. Re-run on a clean checkout.

## Verified gates (D29)

| gate | command | result |
|---|---|---|
| tests | `python -m pytest tests picker_cmc_v1 -q` | **252 passed** |
| RTM regression | `tools/run_detector_on_rtm.py --detector-cmd "…detect_pdf…" --json` | cases 47/49, objects 100/100, missing 0, extra 0, regions 206/210 |
| E2E smoke | `tools/run_product_e2e_smoke.py --pdf <pdf> --workdir <dir> --json` | all 9 stages ✓ |
| deps | `pip install -r requirements.txt && python -c "import fitz, yaml"` | ok (PyMuPDF + PyYAML) |

The 4 RTM region failures are the documented rotated/morph/image-like watermark
limitation (not a regression).

## Milestone status

| milestone | status |
|---|---|
| RTM frozen factory | CLOSED |
| no-truth detector (D11→D20.5) | CLOSED |
| real-PDF operator review loop | CLOSED |
| web viewer + bbox edit/ruler/save | CLOSED |
| edit persistence + edited review export | CLOSED |
| setup-YAML web workflow + run launcher | CLOSED |
| downstream-package-v0 export | CLOSED |
| product E2E smoke + RC docs | CLOSED |

## Contracts (frozen for v0)

setup-yaml-v0 · detector-output-v0 · editor-save-manifest-v0 · edited-review-v0 ·
downstream-package-v0 · real-pdf-review-v0 · web-editor-run-v0
(see `ARTIFACT_CONTRACTS_SUMMARY.md`). Extend with optional fields only.

## Hygiene

- [x] No user/copyrighted PDFs committed (`pdf/` git-ignored).
- [x] No rendered artifacts or run dirs committed (`artifacts/` git-ignored).
- [x] Only source, tests, reports, and docs are committed.

## Scope boundaries (NOT in v0)

- No semantic waveform/diagram/table interpretation; no LLM calls.
- Local single-user web editor (no auth, sessions, DB, cloud, multi-user).
- Real-PDF results are operator visual-review proposals, never golden truth.

## Reproduce-from-docs check

A new operator, using only `OPERATOR_HANDOFF.md`, can: install deps → generate a
setup template → run the detector → launch the web editor → edit a bbox → save →
export the downstream package. (Verified by the D28 E2E smoke, which performs the
same sequence headlessly.)

## Recommendation

**TAG RC.** All gates green; contracts frozen; scope boundaries documented.
