"""Scenario discovery + file load/validation for the RTM CLI (D5.5).

A scenario file (YAML or JSON — YAML is a JSON superset, so one parser covers
both) describes a single case that maps to a CaseSpec. Validation raises
``RtmError`` with a stable error_code, a field path, and allowed_values so an
LLM/agent caller can self-correct.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from .errors import RtmError
from .layout import band, page_dimensions
from .models import (
    CaseSpec,
    FigureSpec,
    HeaderFooterSpec,
    NegativeTextSpec,
    PageSpec,
    TableSpec,
    WatermarkSpec,
)
from .scenario_specs import all_cases
from .templates import (
    FIGURE_CAPTION_TEMPLATES,
    FOOTER_TEMPLATES,
    HEADER_TEMPLATES,
    TABLE_CAPTION_TEMPLATES,
    WATERMARK_TEMPLATES,
)

PAGE_SIZES = ["letter", "a4"]
ORIENTATIONS = ["portrait", "landscape"]
COLUMNS = [1, 2]
FIGURE_BODIES = ["waveform", "diagram", "raster", "mixed"]
FIGURE_ALIASES = list(FIGURE_CAPTION_TEMPLATES)
CAPTION_POSITIONS = ["above", "below"]
WATERMARK_LOCATIONS = ["center", "corner"]


def list_scenarios() -> List[Dict[str, Any]]:
    return [{"case_id": c.case_id, "axes": c.axes, "notes": c.notes} for c in all_cases()]


def list_templates() -> Dict[str, List[Any]]:
    return {
        "header": list(HEADER_TEMPLATES),
        "footer": list(FOOTER_TEMPLATES),
        "watermark": list(WATERMARK_TEMPLATES),
        "table_caption": list(TABLE_CAPTION_TEMPLATES),
        "figure_alias": FIGURE_ALIASES,
        "figure_body": FIGURE_BODIES,
        "caption_position": CAPTION_POSITIONS,
        "watermark_location": WATERMARK_LOCATIONS,
        "page_size": PAGE_SIZES,
        "orientation": ORIENTATIONS,
        "columns": COLUMNS,
    }


def load_scenario_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise RtmError("SCENARIO_FILE_NOT_FOUND", f"scenario file not found: {path}", field="scenario_file")
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RtmError("SCENARIO_FILE_UNREADABLE", f"cannot read scenario file: {exc}", field="scenario_file")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RtmError("SCENARIO_FILE_UNREADABLE", f"cannot parse scenario (YAML/JSON): {exc}", field="scenario_file")
    if not isinstance(data, dict):
        raise RtmError("SCENARIO_INVALID_VALUE", "scenario root must be a mapping", field="scenario")
    return data


# --- validation helpers ------------------------------------------------------
def _enum(value, allowed, code, field):
    if value not in allowed:
        raise RtmError(code, f"invalid value for {field}: {value!r}", field=field, allowed_values=list(allowed))
    return value


def _int(value, field, *, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise RtmError("SCENARIO_INVALID_VALUE", f"{field} must be an integer", field=field)
    if minimum is not None and value < minimum:
        raise RtmError("SCENARIO_INVALID_VALUE", f"{field} must be >= {minimum}", field=field)
    return value


def _bbox(value, page_w, page_h, field):
    if not (isinstance(value, (list, tuple)) and len(value) == 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)):
        raise RtmError("SCENARIO_BAD_BBOX", f"{field} must be 4 numbers [x0,y0,x1,y1]", field=field)
    x0, y0, x1, y1 = value
    if not (x0 < x1 and y0 < y1):
        raise RtmError("SCENARIO_BAD_BBOX", f"{field} must satisfy x0<x1 and y0<y1: {list(value)}", field=field)
    if not (0 <= x0 and x1 <= page_w and 0 <= y0 and y1 <= page_h):
        raise RtmError("SCENARIO_OUT_OF_PAGE_BOUNDS",
                       f"{field} {list(value)} is outside the page {page_w}x{page_h}", field=field)
    return band(x0, y0, x1, y1)


def _header_footer(data, kind, templates, page_w, page_h, page_count):
    if not data:
        return HeaderFooterSpec()
    if not data.get("enabled", False):
        return HeaderFooterSpec()
    tmpl = data.get("text_template")
    if tmpl not in templates:
        raise RtmError("SCENARIO_UNKNOWN_TEMPLATE", f"unknown {kind} template: {tmpl!r}",
                       field=f"{kind}.text_template", allowed_values=list(templates))
    bbox = _bbox(data.get("bbox"), page_w, page_h, f"{kind}.bbox")
    support = data.get("support_pages")
    if support is not None and not (isinstance(support, list) and all(isinstance(s, int) for s in support)):
        raise RtmError("SCENARIO_INVALID_VALUE", f"{kind}.support_pages must be a list of ints", field=f"{kind}.support_pages")
    return HeaderFooterSpec(
        enabled=True, bbox=bbox, text_template=templates[tmpl],
        variable_text=bool(data.get("variable_text", False)),
        mirrored_even_odd=bool(data.get("mirrored_even_odd", False)),
        rule_line=bool(data.get("rule_line", False)),
        support_pages=support,
    )


def scenario_to_casespec(data: Dict[str, Any]) -> CaseSpec:
    """Validate a scenario mapping and build a CaseSpec, or raise RtmError."""
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise RtmError("SCENARIO_INVALID_VALUE", "case_id must be a non-empty string", field="case_id")

    page = data.get("page", {}) or {}
    size = page.get("size", "letter")
    if size not in PAGE_SIZES:
        raise RtmError("SCENARIO_UNSUPPORTED_PAGE_SIZE", f"unsupported page size: {size!r}",
                       field="page.size", allowed_values=PAGE_SIZES)
    orientation = _enum(page.get("orientation", "portrait"), ORIENTATIONS, "SCENARIO_INVALID_VALUE", "page.orientation")
    columns = _enum(page.get("columns", 1), COLUMNS, "SCENARIO_INVALID_VALUE", "page.columns")
    page_count = _int(page.get("page_count", 1), "page.page_count", minimum=1)
    page_offset = _int(page.get("page_offset", 0), "page.page_offset", minimum=0)
    page_w, page_h = page_dimensions(size, orientation)
    page_spec = PageSpec(size=size, orientation=orientation, columns=columns, page_count=page_count, page_offset=page_offset)

    header = _header_footer(data.get("header"), "header", HEADER_TEMPLATES, page_w, page_h, page_count)
    footer = _header_footer(data.get("footer"), "footer", FOOTER_TEMPLATES, page_w, page_h, page_count)

    watermark = WatermarkSpec()
    wm = data.get("watermark")
    if wm and wm.get("enabled", False):
        tmpl = wm.get("text_template")
        if tmpl not in WATERMARK_TEMPLATES:
            raise RtmError("SCENARIO_UNKNOWN_TEMPLATE", f"unknown watermark template: {tmpl!r}",
                           field="watermark.text_template", allowed_values=list(WATERMARK_TEMPLATES))
        wbbox = _bbox(wm.get("bbox"), page_w, page_h, "watermark.bbox")
        location = _enum(wm.get("location", "center"), WATERMARK_LOCATIONS, "SCENARIO_INVALID_VALUE", "watermark.location")
        watermark = WatermarkSpec(
            enabled=True, bbox=wbbox, text_template=WATERMARK_TEMPLATES[tmpl],
            variable_text=bool(wm.get("variable_text", False)),
            rotation_deg=float(wm.get("rotation_deg", 0.0)),
            opacity=float(wm.get("opacity", 0.15)),
            location=location, image_like=bool(wm.get("image_like", False)),
        )

    figures = []
    for i, f in enumerate(data.get("figures", []) or []):
        fld = f"figures[{i}]"
        idx = f.get("index")
        if not isinstance(idx, str) or not idx:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.index must be a non-empty string", field=f"{fld}.index")
        body = _enum(f.get("body_template", "waveform"), FIGURE_BODIES, "SCENARIO_UNKNOWN_TEMPLATE", f"{fld}.body_template")
        alias = _enum(f.get("alias", "Figure"), FIGURE_ALIASES, "SCENARIO_UNKNOWN_TEMPLATE", f"{fld}.alias")
        pos = _enum(f.get("caption_position", "below"), CAPTION_POSITIONS, "SCENARIO_INVALID_VALUE", f"{fld}.caption_position")
        fpage = _int(f.get("page", 1), f"{fld}.page", minimum=1)
        if fpage > page_count:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.page {fpage} exceeds page_count {page_count}", field=f"{fld}.page")
        figures.append(FigureSpec(
            idx, f.get("title", ""),
            _bbox(f.get("caption_region"), page_w, page_h, f"{fld}.caption_region"),
            _bbox(f.get("body_region"), page_w, page_h, f"{fld}.body_region"),
            body_template=body, alias=alias, caption_position=pos, page=fpage,
        ))

    tables = []
    for i, t in enumerate(data.get("tables", []) or []):
        fld = f"tables[{i}]"
        idx = t.get("index")
        if not isinstance(idx, str) or not idx:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.index must be a non-empty string", field=f"{fld}.index")
        gid = t.get("table_group_id")
        if not isinstance(gid, str) or not gid:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.table_group_id must be a non-empty string", field=f"{fld}.table_group_id")
        tpage = _int(t.get("page", 1), f"{fld}.page", minimum=1)
        if tpage > page_count:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.page {tpage} exceeds page_count {page_count}", field=f"{fld}.page")
        tables.append(TableSpec(
            idx, t.get("title", ""),
            _bbox(t.get("caption_region"), page_w, page_h, f"{fld}.caption_region"),
            _bbox(t.get("body_region"), page_w, page_h, f"{fld}.body_region"),
            gid,
            part_index=_int(t.get("part_index", 1), f"{fld}.part_index", minimum=1),
            is_continuation=bool(t.get("is_continuation", False)),
            continuation_marker=t.get("continuation_marker"),
            page=tpage, continued_from=t.get("continued_from"),
            rows=_int(t.get("rows", 8), f"{fld}.rows", minimum=1),
            cols=_int(t.get("cols", 4), f"{fld}.cols", minimum=1),
        ))

    negatives = []
    for i, n in enumerate(data.get("negative_texts", []) or []):
        fld = f"negative_texts[{i}]"
        txt = n.get("text")
        if not isinstance(txt, str) or not txt:
            raise RtmError("SCENARIO_INVALID_VALUE", f"{fld}.text must be a non-empty string", field=f"{fld}.text")
        negatives.append(NegativeTextSpec(txt, _bbox(n.get("bbox"), page_w, page_h, f"{fld}.bbox"),
                                          page=_int(n.get("page", 1), f"{fld}.page", minimum=1)))

    return CaseSpec(
        case_id=case_id, axes=data.get("axes", {"scenario": "custom"}), page=page_spec,
        realistic=bool(data.get("realistic", True)),
        header=header, footer=footer, watermark=watermark,
        figures=tuple(figures), tables=tuple(tables), negative_texts=tuple(negatives),
        notes=data.get("notes", f"Custom scenario {case_id}."),
        coverage_hints=tuple(data.get("coverage_hints", ())),
    )
