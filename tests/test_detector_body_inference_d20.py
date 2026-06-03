"""D20 real-PDF body_region inference (unenclosed diagrams/waveforms + text tables).

Synthetic PDFs only (no user PDF). Verifies that bodies cover the full figure/table
(left signal labels, multi-box diagrams, table rows) without eating a neighbour
caption or interstitial text, and that RTM + the no-truth guarantee are preserved.
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


def _save(doc, tmp_path, name="syn.pdf"):
    p = tmp_path / name
    doc.save(str(p))
    doc.close()
    return p


def test_waveform_figure_includes_left_labels(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(260, 100, 520, 200), color=(0, 0, 0), width=1)   # plot box
    for y, t in ((120, "HCLK"), (140, "HADDR[31:0]"), (160, "HWRITE"), (180, "HRDATA")):
        pg.insert_text((215, y), t, fontsize=8)                              # left signal labels
    pg.insert_text((300, 215), "Figure 1 Read transfer with two wait states", fontsize=10)
    fig = detect_pdf(_save(doc, tmp_path))["pages"][0]["figures"][0]
    body = fig["body_region"]
    assert body[0] <= 240, body          # left edge reaches the labels (left of the plot box at 260)
    assert body[2] >= 515 and body[3] - body[1] >= 80   # still covers the plot box


def test_unenclosed_diagram_full_cluster(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(90, 260, 230, 370), color=(0, 0, 0), width=1)    # left box
    pg.draw_rect(fitz.Rect(380, 260, 520, 370), color=(0, 0, 0), width=1)   # right box (gap, no frame)
    pg.insert_text((230, 385), "Figure 1 Block diagram of the link", fontsize=10)
    fig = detect_pdf(_save(doc, tmp_path))["pages"][0]["figures"][0]
    body = fig["body_region"]
    assert body[0] <= 95 and body[2] >= 515, body   # spans BOTH boxes, not just one


def test_text_table_includes_rows(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.insert_text((80, 110), "Table 1 Measurement results", fontsize=10)
    for i in range(6):                                                       # 6 text rows, no grid
        y = 130 + i * 16
        pg.insert_text((80, y), f"Row {i} label", fontsize=9)
        pg.insert_text((300, y), f"{i*100}", fontsize=9)
    tbl = detect_pdf(_save(doc, tmp_path))["pages"][0]["tables"][0]
    body = tbl["body_region"]
    assert body[3] - body[1] >= 70, body            # covers multiple rows, not just the header
    assert body[2] - body[0] >= 200


def test_body_excludes_next_figure_caption(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 200), color=(0, 0, 0), width=1)
    pg.insert_text((100, 215), "Figure 1 First waveform", fontsize=10)
    pg.draw_rect(fitz.Rect(100, 260, 500, 360), color=(0, 0, 0), width=1)
    pg.insert_text((100, 375), "Figure 2 Second waveform", fontsize=10)
    figs = detect_pdf(_save(doc, tmp_path))["pages"][0]["figures"]
    f1 = next(f for f in figs if f["index"] == "1")
    assert f1["body_region"][3] <= 220, f1          # body 1 stops before figure 2's caption (260+)


def test_body_excludes_interstitial_text(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 220), color=(0, 0, 0), width=1)
    pg.insert_text((100, 235), "Figure 1 A waveform figure", fontsize=10)
    pg.insert_textbox(fitz.Rect(72, 250, 540, 280),                          # interstitial paragraph below
                      "This paragraph discusses the figure in two lines of running text "
                      "that must not be captured as the figure body.", fontsize=9)
    fig = detect_pdf(_save(doc, tmp_path))["pages"][0]["figures"][0]
    assert fig["body_region"][3] <= 240, fig        # body (above the caption) excludes the interstitial


def test_rtm_frozen_body_unchanged(tmp_path):
    # A representative frozen figure case still matches its truth body within tol.
    case = "core_figure_caption_bottom"
    det = detect_pdf(FROZEN / case / f"{case}.pdf")
    truth = json.loads((FROZEN / case / f"{case}.truth.json").read_text())
    tb = truth["pages"][0]["figures"][0]["body_region"]
    db = det["pages"][0]["figures"][0]["body_region"]
    assert all(abs(db[i] - tb[i]) <= 12 for i in range(4)), (db, tb)


def test_no_truth_guarantee(tmp_path):
    doc = fitz.open(); pg = doc.new_page(width=612, height=792)
    pg.draw_rect(fitz.Rect(100, 100, 500, 200), color=(0, 0, 0), width=1)
    pg.insert_text((100, 215), "Figure 1 Example", fontsize=10)
    pdf = _save(doc, tmp_path)
    assert not (tmp_path / "syn.truth.json").exists()
    assert detect_pdf(pdf)["pages"][0]["figures"]   # works with no truth present
