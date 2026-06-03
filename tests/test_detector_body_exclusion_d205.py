"""D20.5 real-PDF body non-target exclusion (Note blocks / prose before a figure).

Keeps D20's full diagram/waveform body but prevents the figure body from swallowing
a preceding Note block, reference sentence, or explanatory paragraph. Synthetic
PDFs only; RTM + no-truth preserved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
FROZEN = PKG / "tests" / "fixtures" / "rtm_frozen"
sys.path.insert(0, str(PKG))

from detector.pipeline import detect_pdf  # noqa: E402


def _waveform_with_preamble(path, *, preamble):
    """A page: a Note/prose preamble, a separator rule, a gap, then a waveform
    (box + left signal labels), then the figure caption below."""
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    if preamble == "note":
        pg.insert_text((150, 110), "Note", fontsize=9)
        pg.insert_textbox(fitz.Rect(120, 120, 540, 150),
                          "For write operations the manager holds the data until the "
                          "subordinate is ready, across two lines of explanatory prose.", fontsize=9)
    elif preamble == "reference":
        pg.insert_textbox(fitz.Rect(120, 120, 540, 145),
                          "Figure 1 shows three transfers to unrelated addresses in the system.", fontsize=9)
    pg.draw_line(fitz.Point(120, 165), fitz.Point(540, 165))      # separator rule (thin)
    # waveform well below the preamble (gap > cluster threshold)
    pg.draw_rect(fitz.Rect(180, 230, 540, 330), color=(0, 0, 0), width=1)
    for y, t in ((250, "HCLK"), (275, "HADDR[31:0]"), (300, "HREADY")):
        pg.insert_text((120, y), t, fontsize=8)                   # left signal labels
    pg.insert_text((150, 350), "Figure 1 Multiple transfers", fontsize=10)
    doc.save(str(path)); doc.close()
    return path


def test_note_block_excluded_waveform_included(tmp_path):
    pdf = _waveform_with_preamble(tmp_path / "n.pdf", preamble="note")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    body = fig["body_region"]
    assert body[1] >= 210, body          # body starts at the waveform, not the Note (y~110)
    assert body[3] >= 320 and body[2] - body[0] >= 300   # full waveform captured


def test_reference_sentence_excluded(tmp_path):
    pdf = _waveform_with_preamble(tmp_path / "r.pdf", preamble="reference")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    assert fig["body_region"][1] >= 210, fig   # "Figure 1 shows..." prose not in the body


def test_left_signal_labels_included(tmp_path):
    pdf = _waveform_with_preamble(tmp_path / "l.pdf", preamble="note")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    assert fig["body_region"][0] <= 130, fig   # left labels (x120) pulled into the body


def test_long_prose_not_in_body(tmp_path):
    pdf = _waveform_with_preamble(tmp_path / "p.pdf", preamble="note")
    fig = detect_pdf(pdf)["pages"][0]["figures"][0]
    # the prose sits at y120-150; the body must start below it
    assert fig["body_region"][1] > 150, fig


def test_rtm_frozen_regression(tmp_path):
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4)), (db, tb)


def test_no_truth_guarantee(tmp_path):
    pdf = _waveform_with_preamble(tmp_path / "g.pdf", preamble="note")
    assert not (tmp_path / "g.truth.json").exists()
    assert detect_pdf(pdf)["pages"][0]["figures"]
