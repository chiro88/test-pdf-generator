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


def page_jitter(page_no: int, amp_x: int, amp_y: int) -> tuple[float, float]:
    """Deterministic small per-page offset (no RNG), each axis in [-amp, +amp].

    Multipliers (3, 2) are kept coprime to the moduli (2*amp+1) so the offset
    actually varies page to page rather than collapsing to a constant.
    """
    dx = ((page_no * 3) % (2 * amp_x + 1)) - amp_x if amp_x else 0
    dy = ((page_no * 2) % (2 * amp_y + 1)) - amp_y if amp_y else 0
    return float(dx), float(dy)


def jittered_bbox(bbox: BBox, page_no: int, amp_x: int, amp_y: int) -> BBox:
    dx, dy = page_jitter(page_no, amp_x, amp_y)
    return BBox(bbox.x0 + dx, bbox.y0 + dy, bbox.x1 + dx, bbox.y1 + dy)
