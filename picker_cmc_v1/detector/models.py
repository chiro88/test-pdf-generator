"""Lightweight value objects for the detector pipeline (D11)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TextLine:
    text: str
    bbox: List[float]


@dataclass
class PageExtract:
    page: int
    width: float
    height: float
    lines: List[TextLine] = field(default_factory=list)
    drawings: List[List[float]] = field(default_factory=list)  # vector graphic rects [x0,y0,x1,y1]


@dataclass
class Anchor:
    kind: str            # "figure" | "table"
    index: str
    title: str
    caption_bbox: List[float]


@dataclass
class InferredRegion:
    body: List[float]
    context: List[float]
    title_position: str
    title_body_gap_lines: int
    confident: bool = True
