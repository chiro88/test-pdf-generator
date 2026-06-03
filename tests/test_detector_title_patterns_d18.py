"""D18 real-PDF Figure/Table title pattern expansion (no-colon ARM-style).

Adds no-colon caption support ("Figure 3-3 Read transfer …") while preserving the
reference-sentence false-positive guards and the existing RTM/punctuated forms.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "picker_cmc_v1"
sys.path.insert(0, str(PKG))

from detector.title_patterns import match_caption  # noqa: E402

SAMPLE1 = ROOT / "pdf" / "dp_sample1.pdf"   # local-only user PDF (not committed)


# (1)(2) no-colon ARM-style captions accepted
@pytest.mark.parametrize("text,kind,index", [
    ("Figure 3-3 Read transfer with two wait states", "figure", "3-3"),
    ("Figure 3-4 Write transfer with one wait state", "figure", "3-4"),
    ("Figure 3-5 Multiple transfers", "figure", "3-5"),
    ("Table 3-1 Transfer type encoding", "table", "3-1"),
    ("Fig. A.1 Example waveform timing", "figure", "A.1"),
    ("FIGURE 2-7 Example title", "figure", "2-7"),
])
def test_no_colon_caption_accepted(text, kind, index):
    m = match_caption(text)
    assert m is not None and m[0] == kind and m[1] == index


# (3)(4)(5) reference sentences rejected
@pytest.mark.parametrize("text", [
    "Figure 3-3 shows a read transfer with two wait states.",
    "Figure 3-5 shows three transfers and a final response.",
    "Table 3-1 lists the transfer type encodings.",
    "Table 5-2 summarizes the results.",
    "Figure 3-4 illustrates the timing.",
    "In Figure 3-5:",
    "see Table 3-1",
])
def test_reference_sentences_rejected(text):
    assert match_caption(text) is None


# (6) existing RTM punctuated patterns still accepted
@pytest.mark.parametrize("text,kind,index", [
    ("Figure 3.4. Waveform timing", "figure", "3.4"),
    ("Fig. A.1. Reset path", "figure", "A.1"),
    ("FIGURE 2-7. Datapath", "figure", "2-7"),
    ("Figure 12. Output", "figure", "12"),
    ("Table 3-1. Bus map", "table", "3-1"),
    ("Table 2.1. Register map (cont)", "table", "2.1"),
    ("Figure 1-1: DP Data Transport Channels", "figure", "1-1"),
])
def test_punctuated_patterns_preserved(text, kind, index):
    m = match_caption(text)
    assert m is not None and m[0] == kind and m[1] == index


# (7) negative FP corpus still produces no anchors
@pytest.mark.parametrize("text", [
    "Figure of merit is defined as the ratio of useful output to input power.",
    "For configuration details, see Table above in the previous section.",
    "Figure 3.4 is referenced for historical context only; the diagram is not reproduced.",
    "Table 2.1 describes the legacy configuration in an earlier revision; not reproduced.",
])
def test_negative_corpus_zero_fp(text):
    assert match_caption(text) is None


# capitalised positional title words must survive (not over-blocked)
@pytest.mark.parametrize("text", [
    "Figure 5 On-chip memory map",
    "Figure 6 Above-threshold detection",
])
def test_capitalised_positional_titles_survive(text):
    assert match_caption(text) is not None


# (8) real-PDF smoke: dp_sample1 detects >=3 figures and >=1 table (if sample present)
@pytest.mark.skipif(not SAMPLE1.exists(), reason="local user PDF dp_sample1.pdf not available")
def test_dp_sample1_smoke_detects_arm_captions(tmp_path):
    from detector.review_artifacts import build_review_package
    summary = build_review_package(SAMPLE1, tmp_path / "out")
    assert summary["figures_detected"] >= 3, summary
    assert summary["tables_detected"] >= 1, summary
