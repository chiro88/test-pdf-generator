"""D17 real-PDF smoke / operator review harness tests (no truth).

All tests use a SYNTHETIC small PDF generated in-process — never a user-provided
PDF. They exercise the review package: manifest, review_index.md, overlays,
crops, --json output, structured error on bad input, validator pass, and the
no-truth guarantee.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from detector.review_artifacts import ReviewInputError, build_review_package  # noqa: E402
from detector_output.validator import validate_manifest  # noqa: E402

RUNNER = PKG / "tools" / "run_detector_on_pdf.py"


def _make_pdf(path: Path) -> None:
    """A tiny PDF with one captioned figure and one captioned table (framed bodies)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Figure: a framed body with a caption line directly below it.
    page.draw_rect(fitz.Rect(80, 110, 530, 300), color=(0, 0, 0), width=1.0)
    page.insert_text((80, 315), "Figure 1. Synthetic waveform under review", fontsize=10)
    # Table: a framed body with a caption line above it.
    page.insert_text((80, 430), "Table 1. Synthetic measurement table", fontsize=10)
    page.draw_rect(fitz.Rect(80, 440, 530, 640), color=(0, 0, 0), width=1.0)
    # A running header + footer so common regions are exercised.
    page.insert_textbox(fitz.Rect(48, 18, 564, 40), "Synthetic Spec — Section 1", fontsize=9, align=1)
    page.insert_textbox(fitz.Rect(48, 752, 564, 774), "Synthetic — Page 1", fontsize=9, align=1)
    doc.save(str(path))
    doc.close()


def test_creates_manifest_index_overlay(tmp_path):
    pdf = tmp_path / "syn.pdf"; _make_pdf(pdf)
    out = tmp_path / "out"
    summary = build_review_package(pdf, out)
    assert summary["ok"] and summary["pages"] == 1
    assert (out / "detected_manifest.json").exists()      # (1)
    assert (out / "review_index.md").exists()             # (2)
    assert (out / "pages" / "page_001_overlay.png").exists()  # (3)


def test_crop_generated_for_object(tmp_path):
    pdf = tmp_path / "syn.pdf"; _make_pdf(pdf)
    out = tmp_path / "out"
    summary = build_review_package(pdf, out)
    # at least one figure/table detected -> at least one body crop on disk (4)
    assert summary["figures_detected"] + summary["tables_detected"] >= 1
    crops = list((out / "crops").glob("*_body.png"))
    assert crops, "expected at least one body crop"


def test_manifest_validates(tmp_path):
    pdf = tmp_path / "syn.pdf"; _make_pdf(pdf)
    out = tmp_path / "out"
    build_review_package(pdf, out)
    manifest = json.loads((out / "detected_manifest.json").read_text())
    assert validate_manifest(manifest) == []              # (7)


def test_no_truth_required(tmp_path):
    pdf = tmp_path / "syn.pdf"; _make_pdf(pdf)
    out = tmp_path / "out"
    build_review_package(pdf, out)
    # no truth file anywhere near the input or output (8)
    assert not (tmp_path / "syn.truth.json").exists()
    assert not list(out.rglob("*truth*"))


def test_cli_json_is_pure_json(tmp_path):
    pdf = tmp_path / "syn.pdf"; _make_pdf(pdf)
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, str(RUNNER), "--pdf", str(pdf), "--out", str(out), "--json"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)                     # (5) pure JSON
    assert payload["ok"] and payload["artifacts"]["manifest"]


def test_cli_invalid_pdf_structured_error(tmp_path):
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, str(RUNNER), "--pdf", str(tmp_path / "missing.pdf"),
                           "--out", str(out), "--json"], capture_output=True, text=True)
    assert proc.returncode == 2                           # (6)
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and payload["error_code"] == "INVALID_PDF_INPUT"
