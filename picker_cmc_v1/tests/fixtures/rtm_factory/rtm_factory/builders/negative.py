from __future__ import annotations

import fitz

from ..models import NegativeTextSpec


def draw_negative_text(page: fitz.Page, spec: NegativeTextSpec) -> None:
    page.insert_textbox(fitz.Rect(*spec.bbox.to_list()), spec.text, fontsize=10, fontname="helv", align=0)
