"""D16.5 common-region/watermark truth-contract correction (no-truth).

GPT decision B: the multipart-footer fragment bboxes and the extractable rot0
license watermark bbox are corrected from authored editorial rectangles to the
PDF-derivable rendered-text band, so a truth-blind detector can match them.
Rotated / morph / image-like watermarks keep their authored band and remain a
documented limitation (NOT forced to pass).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector.pipeline import detect_pdf  # noqa: E402


def _truth_commons(cid):
    t = json.loads((FROZEN / cid / f"{cid}.truth.json").read_text())
    return [[r["kind"], [round(v, 2) for v in r["bbox"]]]
            for p in t["pages"] for r in p["common_regions"]]


def _det_commons(cid):
    d = detect_pdf(FROZEN / cid / f"{cid}.pdf")
    return [[c["kind"], [round(v, 2) for v in c["bbox"]]]
            for p in d["pages"] for c in p["common_regions"]]


def test_multipart_footer_truth_is_pdf_derivable():
    cid = "exp_hf_multipart_footer_center_notice"
    # corrected truth == what a truth-blind detector derives from the PDF.
    assert _det_commons(cid) == _truth_commons(cid)


def test_license_watermark_truth_is_pdf_derivable():
    cid = "exp_wm_license_text_position_jitter"
    assert _det_commons(cid) == _truth_commons(cid)


def test_rotated_morph_watermark_stays_limitation():
    # These keep authored bands; the detector cannot match them within tolerance.
    # They must NOT have been silently coerced to match (truth != detector here).
    for cid in ("core_fixed_watermark", "exp_wm_near_footer_rotation_opacity_jitter"):
        assert _det_commons(cid) != _truth_commons(cid), cid
