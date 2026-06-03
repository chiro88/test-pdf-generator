"""Figure/table caption title-anchor patterns (D11 + D18).

A caption is "<alias> <index><sep> <title>". Two real-world separator forms are
accepted:

  * punctuated:  "Figure 3.4. Waveform timing" / "Table 1-7: Bandwidth"
      a '.' or ':' immediately after the index, then the title.
  * no-colon (ARM-style):  "Figure 3-3 Read transfer with two wait states"
      whitespace after the index, then a title phrase.

The no-colon form is permissive, so it is paired with a reference-sentence guard
(D18): a line whose text after the index reads like prose — "Figure 3-3 shows …",
"Table 2.1 describes …", "Figure 3.4 is referenced …" — is rejected. The guard
keys on the first title word: an all-lowercase first word (a sentence
continuation) or an explicit reference verb is rejected; a capitalised title
phrase ("Read transfer …", "Transfer type encoding") is accepted. Lines that do
not start with the alias ("In Figure 3-5:", "see Table above") never match, and a
"Figure of merit" line has no numeric index so it never matches either.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# index styles: 3.4, 12, 2-7, A.1, 3-4, 3-3
_INDEX = r"[A-Za-z]{0,2}\.?\d+(?:[.\-]\d+)*"
# alias + index, then the remainder (separator/title) captured for inspection.
_HEAD_RE = re.compile(r"^\s*(Figure|Fig\.|FIGURE|Table)\s+(" + _INDEX + r")(.*)$")
# punctuated separator: '.' or ':' right after the index, then whitespace + title.
_PUNCT_RE = re.compile(r"^[.:]\s+(\S.*)$")
# no-colon separator: whitespace, then the title phrase.
_SPACE_RE = re.compile(r"^\s+(\S.*)$")
# first alphabetic word of a title (handles leading punctuation, keeps hyphens).
_FIRST_WORD_RE = re.compile(r"[^A-Za-z]*([A-Za-z][\w'\-]*)")

# Reference verbs that mark prose even when capitalised at a sentence start.
# (Positional words in/on/above/below are intentionally NOT here so capitalised
# titles like "On-chip memory map" survive; their lowercase prose forms are
# caught by the all-lowercase guard below.)
_REJECT_VERBS = {
    "shows", "illustrates", "lists", "describes", "depicts", "presents",
    "summarizes", "summarises", "is", "are", "was", "were", "see",
}

# continuation markers that may trail a (table) title
_CONT_MARKERS = ["(continued)", "(cont)", "continued", "Continued", "cont."]


def _looks_like_reference(title: str) -> bool:
    """True if a no-colon title reads like a reference sentence, not a caption."""
    m = _FIRST_WORD_RE.match(title)
    if not m:
        return True                      # no real title word -> not a caption
    first = m.group(1)
    if first.lower() in _REJECT_VERBS:
        return True                      # "shows" / "Lists" / "is" ...
    if first.islower():
        return True                      # any all-lowercase first word = prose
    return False


def match_caption(text: str) -> Optional[Tuple[str, str, str]]:
    """Return (kind, index, title) for a caption line, else None."""
    m = _HEAD_RE.match(text or "")
    if not m:
        return None
    word, index, rest = m.group(1), m.group(2), m.group(3)
    kind = "table" if word.lower().startswith("table") else "figure"

    mp = _PUNCT_RE.match(rest)
    if mp:                               # punctuated form: always a caption
        return kind, index, mp.group(1).strip()

    ms = _SPACE_RE.match(rest)
    if ms:                               # no-colon form: guard against prose
        title = ms.group(1).strip()
        if not _looks_like_reference(title):
            return kind, index, title
    return None


def continuation_marker(title: str) -> Optional[str]:
    t = (title or "").strip()
    for mk in _CONT_MARKERS:
        if t.endswith(mk):
            return mk
    return None
