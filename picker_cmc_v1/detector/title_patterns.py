"""Figure/table caption title-anchor patterns (D11).

A real RTM caption is "<alias> <index>. <title>" — the index is followed by a
period/colon. Inline references ("Figure 3.4 is referenced", "Table 2.1
describes", "Figure of merit", "see Table above") lack that pattern, so they do
NOT match — which is exactly how the negative cases avoid false anchors.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# index styles: 3.4, 12, 2-7, A.1, 3-4
_INDEX = r"[A-Za-z]{0,2}\.?\d+(?:[.\-]\d+)*"
# The caption separator must be a [.:] IMMEDIATELY after the (full) index and
# then whitespace, e.g. "Figure 3.4. Title". An inline reference like
# "Figure 3.4 is referenced" has a space (not a period) after the index, so it
# does not match — and backtracking to index "3" fails because the "." in "3.4"
# is not followed by whitespace. This is what keeps the negative cases clean.
_CAPTION_RE = re.compile(r"^\s*(Figure|Fig\.|FIGURE|Table)\s+(" + _INDEX + r")[.:]\s+(.+)$")

# continuation markers that may trail a (table) title
_CONT_MARKERS = ["(continued)", "(cont)", "continued", "Continued", "cont."]


def match_caption(text: str) -> Optional[Tuple[str, str, str]]:
    """Return (kind, index, title) for a caption line, else None."""
    m = _CAPTION_RE.match(text or "")
    if not m:
        return None
    word, index, title = m.group(1), m.group(2), m.group(3).strip()
    kind = "table" if word.lower().startswith("table") else "figure"
    return kind, index, title


def continuation_marker(title: str) -> Optional[str]:
    t = (title or "").strip()
    for mk in _CONT_MARKERS:
        if t.endswith(mk):
            return mk
    return None
