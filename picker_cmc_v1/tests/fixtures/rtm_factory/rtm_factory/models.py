from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple


Kind = Literal["figure", "table", "header", "footer", "watermark"]


@dataclass(frozen=True)
class BBox:
    """Top-left PDF point coordinates: [x0, y0, x1, y1]."""

    x0: float
    y0: float
    x1: float
    y1: float

    def to_list(self) -> List[float]:
        return [round(self.x0, 2), round(self.y0, 2), round(self.x1, 2), round(self.y1, 2)]

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def expanded(self, margin: float, page_width: float, page_height: float) -> "BBox":
        return BBox(
            max(0.0, self.x0 - margin),
            max(0.0, self.y0 - margin),
            min(page_width, self.x1 + margin),
            min(page_height, self.y1 + margin),
        )

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )


@dataclass(frozen=True)
class PageSpec:
    size: Literal["letter", "a4"] = "letter"
    orientation: Literal["portrait", "landscape"] = "portrait"
    columns: Literal[1, 2] = 1
    page_count: int = 1
    page_offset: int = 0


@dataclass(frozen=True)
class HeaderFooterSpec:
    enabled: bool = False
    bbox: Optional[BBox] = None
    text_template: str = ""
    variable_text: bool = False
    mirrored_even_odd: bool = False
    rule_line: bool = False
    support_pages: Optional[Sequence[int]] = None
    # D7 realism: kind is used for extra_regions; jitter amplitudes (pt) drive
    # deterministic per-page offsets; first_page_suppressed hides page 1.
    kind: str = ""
    jitter_x: int = 0
    jitter_y: int = 0
    rule_jitter_y: int = 0
    first_page_suppressed: bool = False
    # D16.5: record the PDF-derivable rendered-text band as truth (so a truth-blind
    # detector can match it) instead of the authored spec bbox.
    band_from_text: bool = False


@dataclass(frozen=True)
class WatermarkSpec:
    enabled: bool = False
    bbox: Optional[BBox] = None
    text_template: str = "DRAFT"
    variable_text: bool = False
    rotation_deg: float = 0.0
    opacity: float = 0.15
    location: Literal["center", "corner"] = "center"
    image_like: bool = False
    # D7 realism: deterministic per-page jitter amplitudes.
    jitter_pos: int = 0
    jitter_rot: float = 0.0
    jitter_opacity: float = 0.0
    near_footer: bool = False
    # D16.5: record the PDF-derivable rendered-text band as truth (extractable
    # rot0 watermarks only; rotated/morph/image-like keep the authored band).
    band_from_text: bool = False


@dataclass(frozen=True)
class FigureSpec:
    index: str
    title: str
    caption_region: BBox
    body_region: BBox
    body_template: Literal["waveform", "diagram", "raster", "mixed"] = "waveform"
    alias: Literal["Figure", "Fig.", "FIGURE"] = "Figure"
    caption_position: Literal["above", "below"] = "below"
    page: int = 1
    context_margin: float = 8.0


@dataclass(frozen=True)
class TableSpec:
    index: str
    title: str
    caption_region: BBox
    body_region: BBox
    table_group_id: str
    part_index: int = 1
    is_continuation: bool = False
    continuation_marker: Optional[str] = None
    page: int = 1
    continued_from: Optional[str] = None
    context_margin: float = 8.0
    rows: int = 8
    cols: int = 4
    caption_position: Literal["above", "below"] = "above"


@dataclass(frozen=True)
class InterstitialTextSpec:
    """Controlled body text (1-2 lines) placed BETWEEN two targets in a sequence."""
    bbox: BBox
    line_count: int = 1
    text: str = ""
    between: Optional[Tuple[str, str]] = None
    page: int = 1


@dataclass(frozen=True)
class NegativeTextSpec:
    text: str
    bbox: BBox
    page: int = 1


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    axes: Dict[str, Any]
    page: PageSpec
    realistic: bool = True
    header: HeaderFooterSpec = field(default_factory=HeaderFooterSpec)
    footer: HeaderFooterSpec = field(default_factory=HeaderFooterSpec)
    watermark: WatermarkSpec = field(default_factory=WatermarkSpec)
    figures: Tuple[FigureSpec, ...] = ()
    tables: Tuple[TableSpec, ...] = ()
    negative_texts: Tuple[NegativeTextSpec, ...] = ()
    notes: str = ""
    coverage_hints: Tuple[str, ...] = ()
    # D7: additional header/footer regions (e.g. multi-part left/center/right footer).
    extra_regions: Tuple[HeaderFooterSpec, ...] = ()
    # D9: when true, generic body text is allowed to overlap target regions
    # (an explicit overlap stress case); otherwise self_check fails on overlap.
    intentional_overlap_stress: bool = False
    # D9 step2: controlled interstitial text between targets + ordered layout sequence.
    interstitial_texts: Tuple[InterstitialTextSpec, ...] = ()
    layout_sequence: Tuple[Dict[str, Any], ...] = ()


@dataclass(frozen=True)
class RegionTruth:
    kind: Kind
    bbox: BBox
    text: Optional[str] = None
    variable_text: bool = False
    rotation_deg: Optional[float] = None

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": self.kind, "bbox": self.bbox.to_list()}
        if self.text is not None:
            out["text"] = self.text
        if self.variable_text:
            out["variable_text"] = True
        if self.rotation_deg is not None:
            out["rotation_deg"] = self.rotation_deg
        return out


@dataclass(frozen=True)
class FigureTruth:
    kind: Literal["figure"]
    index: str
    title: str
    caption_region: BBox
    body_region: BBox
    context_region: BBox
    body_kind: str
    title_position: str = "below"
    title_body_gap_lines: int = 0

    def to_json(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "index": self.index,
            "title": self.title,
            "caption_region": self.caption_region.to_list(),
            "body_region": self.body_region.to_list(),
            "context_region": self.context_region.to_list(),
            "body_kind": self.body_kind,
            "title_position": self.title_position,
            "title_body_gap_lines": self.title_body_gap_lines,
        }


@dataclass(frozen=True)
class TableTruth:
    kind: Literal["table"]
    index: str
    title: str
    table_group_id: str
    part_index: int
    is_continuation: bool
    continuation_marker: Optional[str]
    caption_region: BBox
    body_region: BBox
    context_region: Optional[BBox] = None
    continued_from: Optional[str] = None
    title_position: str = "above"
    title_body_gap_lines: int = 0

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "kind": self.kind,
            "index": self.index,
            "title": self.title,
            "table_group_id": self.table_group_id,
            "part_index": self.part_index,
            "is_continuation": self.is_continuation,
            "continuation_marker": self.continuation_marker,
            "caption_region": self.caption_region.to_list(),
            "body_region": self.body_region.to_list(),
            "title_position": self.title_position,
            "title_body_gap_lines": self.title_body_gap_lines,
        }
        if self.context_region is not None:
            out["context_region"] = self.context_region.to_list()
        if self.continued_from is not None:
            out["continued_from"] = self.continued_from
        return out


@dataclass
class NonTargetTruth:
    """A non-target text band: generic body filler or controlled interstitial text."""
    bbox: BBox
    role: str = "body_filler"            # body_filler | interstitial_text
    line_count: Optional[int] = None
    between: Optional[Tuple[str, str]] = None

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": "non_target_text", "bbox": self.bbox.to_list(), "role": self.role}
        if self.line_count is not None:
            out["line_count"] = self.line_count
        if self.between is not None:
            out["between"] = list(self.between)
        return out


@dataclass
class PageTruth:
    page: int
    width: float
    height: float
    common_regions: List[RegionTruth] = field(default_factory=list)
    figures: List[FigureTruth] = field(default_factory=list)
    tables: List[TableTruth] = field(default_factory=list)
    # D9: interstitial / body text bands that are NOT detection targets.
    non_target_text_regions: List[NonTargetTruth] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "common_regions": [r.to_json() for r in self.common_regions],
            "figures": [f.to_json() for f in self.figures],
            "tables": [t.to_json() for t in self.tables],
            "non_target_text_regions": [n.to_json() for n in self.non_target_text_regions],
        }
