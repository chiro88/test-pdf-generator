"""Deterministic band-based vertical layout engine for D9 sequence cases.

Stacks figures / tables / interstitial-text top-to-bottom in the body band with
controlled title position and title-body gaps, and emits the FigureSpec /
TableSpec / InterstitialTextSpec objects plus a ``layout_sequence`` record so a
detector's answer key can verify ordering and non-target interstitial text.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .layout import band
from .models import CaseSpec, FigureSpec, InterstitialTextSpec, PageSpec, TableSpec

LINE = 12.0          # one text line, in points (used for gaps + interstitial heights)
CAP_H = 18.0         # single-line caption height
ITEM_GAP = 12.0      # vertical separation between consecutive sequence items
BODY_TOP = 96.0


class SequenceBuilder:
    """Author a single-page vertical sequence of targets + interstitial text."""

    def __init__(self, *, x0: float = 54.0, x1: float = 558.0, top: float = BODY_TOP, page: int = 1):
        self.x0 = x0
        self.x1 = x1
        self.y = top
        self.page = page
        self.figures: List[FigureSpec] = []
        self.tables: List[TableSpec] = []
        self._interstitials: List[InterstitialTextSpec] = []
        self.sequence: List[Dict[str, Any]] = []

    # --- items ---------------------------------------------------------------
    def figure(self, index: str, title: str, *, body_kind: str = "waveform", alias: str = "Figure",
               caption_pos: str = "below", gap_lines: int = 1, body_h: float = 150.0) -> "SequenceBuilder":
        gap = gap_lines * LINE
        if caption_pos == "below":
            body = band(self.x0, self.y, self.x1, self.y + body_h)
            cap = band(self.x0, self.y + body_h + gap, self.x1, self.y + body_h + gap + CAP_H)
            bottom = self.y + body_h + gap + CAP_H
        else:
            cap = band(self.x0, self.y, self.x1, self.y + CAP_H)
            body = band(self.x0, self.y + CAP_H + gap, self.x1, self.y + CAP_H + gap + body_h)
            bottom = self.y + CAP_H + gap + body_h
        self.figures.append(FigureSpec(index, title, cap, body, body_template=body_kind, alias=alias,
                                       caption_position=caption_pos, page=self.page))
        self.sequence.append({"type": "figure", "id": index})
        self.y = bottom + ITEM_GAP
        return self

    def table(self, index: str, title: str, group: str, *, caption_pos: str = "above", gap_lines: int = 1,
              body_h: float = 170.0, rows: int = 7, cols: int = 4, part: int = 1,
              cont: bool = False, marker: Optional[str] = None) -> "SequenceBuilder":
        gap = gap_lines * LINE
        if caption_pos == "below":
            body = band(self.x0, self.y, self.x1, self.y + body_h)
            cap = band(self.x0, self.y + body_h + gap, self.x1, self.y + body_h + gap + CAP_H)
            bottom = self.y + body_h + gap + CAP_H
        else:
            cap = band(self.x0, self.y, self.x1, self.y + CAP_H)
            body = band(self.x0, self.y + CAP_H + gap, self.x1, self.y + CAP_H + gap + body_h)
            bottom = self.y + CAP_H + gap + body_h
        self.tables.append(TableSpec(index, title, cap, body, group, part_index=part, is_continuation=cont,
                                     continuation_marker=marker, page=self.page, rows=rows, cols=cols,
                                     caption_position=caption_pos))
        self.sequence.append({"type": "table", "id": index})
        self.y = bottom + ITEM_GAP
        return self

    def text(self, line_count: int = 1) -> "SequenceBuilder":
        h = line_count * LINE
        bbox = band(self.x0, self.y, self.x1, self.y + h)
        self._interstitials.append(InterstitialTextSpec(bbox, line_count=line_count, page=self.page))
        self.sequence.append({"type": "non_target_text", "line_count": line_count})
        self.y = h + self.y + ITEM_GAP
        return self

    # --- assembly ------------------------------------------------------------
    def _resolve_between(self) -> Tuple[InterstitialTextSpec, ...]:
        """Fill each interstitial's `between` = (prev target label, next target label)."""
        labels: List[Optional[str]] = []
        for item in self.sequence:
            if item["type"] in ("figure", "table"):
                labels.append(f"{item['type']}:{item['id']}")
            else:
                labels.append(None)
        out: List[InterstitialTextSpec] = []
        it_iter = iter(self._interstitials)
        for i, item in enumerate(self.sequence):
            if item["type"] != "non_target_text":
                continue
            prev_label = next((labels[j] for j in range(i - 1, -1, -1) if labels[j]), None)
            next_label = next((labels[j] for j in range(i + 1, len(labels)) if labels[j]), None)
            spec = next(it_iter)
            between = (prev_label, next_label) if (prev_label or next_label) else None
            out.append(InterstitialTextSpec(spec.bbox, line_count=spec.line_count, between=between, page=spec.page))
        return tuple(out)

    def build_case(self, case_id: str, axes: Dict[str, Any], *, notes: str = "", coverage_hints: Tuple[str, ...] = (),
                   header=None, footer=None, extra_regions: Tuple = (), page_count: int = 1, page_offset: int = 0,
                   watermark=None) -> CaseSpec:
        from .models import HeaderFooterSpec, WatermarkSpec
        kw: Dict[str, Any] = {}
        if header is not None:
            kw["header"] = header
        if footer is not None:
            kw["footer"] = footer
        if watermark is not None:
            kw["watermark"] = watermark
        return CaseSpec(
            case_id=case_id, axes=axes, page=PageSpec(page_count=page_count, page_offset=page_offset),
            figures=tuple(self.figures), tables=tuple(self.tables),
            interstitial_texts=self._resolve_between(),
            layout_sequence=tuple(self.sequence),
            notes=notes or f"Sequence case {case_id}.",
            coverage_hints=coverage_hints, extra_regions=extra_regions, **kw,
        )
