"""PyMuPDF extraction layer (D11) — text lines + vector drawing rects, top-left pt."""
from __future__ import annotations

from pathlib import Path
from typing import List

import fitz

from .models import PageExtract, TextLine


def extract_page(page: "fitz.Page", page_no: int) -> PageExtract:
    lines: List[TextLine] = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if txt:
                lines.append(TextLine(txt, [round(c, 2) for c in line["bbox"]]))
    drawings: List[List[float]] = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > 0 and r.height > 0:
            drawings.append([round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)])
    return PageExtract(page=page_no, width=page.rect.width, height=page.rect.height, lines=lines, drawings=drawings)


def extract_pdf(path: str | Path) -> List[PageExtract]:
    doc = fitz.open(str(path))
    try:
        return [extract_page(doc[i], i + 1) for i in range(doc.page_count)]
    finally:
        doc.close()
