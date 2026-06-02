# RTM Acceptance Gate

## Absolute rule

A detector task is not accepted because pytest passes. It is accepted only when it passes real PDF fixture comparison.

## Gate stages

### Gate A — RTM Factory Generation

Pass criteria:

```text
python picker_cmc_v1/tests/fixtures/rtm_factory/generate.py
```

must create:

```text
rtm_gallery/MANIFEST.json
rtm_gallery/index.md
rtm_gallery/<case_id>/<case_id>.pdf
rtm_gallery/<case_id>/<case_id>.truth.json
rtm_gallery/<case_id>/<case_id>.pNN.png
rtm_gallery/<case_id>/<case_id>.notes.md
```

and `self_check.py` must pass.

### Gate B — Human Review

The user reviews `rtm_gallery/index.md` and fills:

```text
realism 1-5
keep/drop
critique
```

Only keep cases may be promoted.

### Gate C — Frozen Fixture Promotion

Keep cases are copied to:

```text
picker_cmc_v1/tests/fixtures/rtm_frozen/
```

with `FROZEN_MANIFEST.json`.

### Gate D — Detector Golden Comparison

Detector output must be compared to frozen truth JSON with tolerance.

Required outputs:

```text
artifacts/rtm_compare/<case_id>/detected_manifest.json
artifacts/rtm_compare/<case_id>/diff_report.md
artifacts/rtm_compare/<case_id>/page_NNN_overlay.png
```

### Gate E — Regression Lock

Once a frozen fixture exists, cc-coder must not update its truth JSON just to make detector pass. Truth updates require explicit review and a diff report.

## Required failure visibility

Any mismatch must produce:

```text
- failing case_id
- page number
- region kind
- expected bbox
- detected bbox
- delta values
- tolerance used
- overlay PNG path
```
