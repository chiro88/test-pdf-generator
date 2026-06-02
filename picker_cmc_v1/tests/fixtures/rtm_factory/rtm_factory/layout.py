from __future__ import annotations

from .models import BBox

PAGE_SIZES = {
    "letter": (612.0, 792.0),
    "a4": (595.0, 842.0),
}


def page_dimensions(size: str, orientation: str) -> tuple[float, float]:
    width, height = PAGE_SIZES[size]
    if orientation == "landscape":
        return height, width
    return width, height


def band(x0: float, y0: float, x1: float, y1: float) -> BBox:
    return BBox(float(x0), float(y0), float(x1), float(y1))


def context_from(caption: BBox, body: BBox, margin: float, page_width: float, page_height: float) -> BBox:
    return caption.union(body).expanded(margin, page_width, page_height)


def mirrored_x_bbox(bbox: BBox, page_width: float) -> BBox:
    width = bbox.width
    return BBox(page_width - bbox.x0 - width, bbox.y0, page_width - bbox.x0, bbox.y1)


def assert_bbox_in_page(bbox: BBox, width: float, height: float, label: str) -> None:
    if not (0 <= bbox.x0 < bbox.x1 <= width and 0 <= bbox.y0 < bbox.y1 <= height):
        raise ValueError(f"{label} bbox out of page bounds: {bbox} for {width}x{height}")
