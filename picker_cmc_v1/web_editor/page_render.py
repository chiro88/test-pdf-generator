"""D23 page rasterization for the viewer (read-only)."""
from __future__ import annotations

from pathlib import Path

import fitz


def render_page_png(pdf_path: str | Path, page: int, scale: float = 1.5) -> bytes:
    """Render one 1-based PDF page to PNG bytes at ``scale`` (top-left, no flip)."""
    doc = fitz.open(str(pdf_path))
    try:
        if page < 1 or page > doc.page_count:
            raise ValueError(f"page {page} out of range (1..{doc.page_count})")
        pix = doc[page - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()
