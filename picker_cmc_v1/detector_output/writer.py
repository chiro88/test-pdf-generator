"""detector-output-v0 manifest writer/builder (D10).

Helpers to assemble and persist a contract-valid detected manifest. Building a
manifest here is just I/O — it makes no correctness claim about its contents.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schema
from .validator import validate_or_raise


def figure(index: str, title: str, caption: list, body: list, context: list, *,
           title_position: str = "below", title_body_gap_lines: int = 0) -> Dict[str, Any]:
    return {
        "kind": "figure", "index": index, "title": title,
        "caption_region": caption, "body_region": body, "context_region": context,
        "title_position": title_position, "title_body_gap_lines": title_body_gap_lines,
    }


def table(index: str, title: str, group: str, caption: list, body: list, context: Optional[list] = None, *,
          part_index: int = 1, is_continuation: bool = False, continuation_marker: Optional[str] = None,
          continued_from: Optional[str] = None) -> Dict[str, Any]:
    out = {
        "kind": "table", "index": index, "title": title, "table_group_id": group,
        "part_index": part_index, "is_continuation": is_continuation, "continuation_marker": continuation_marker,
        "caption_region": caption, "body_region": body,
    }
    if context is not None:
        out["context_region"] = context
    if continued_from is not None:
        out["continued_from"] = continued_from
    return out


def common_region(kind: str, bbox: list, text: Optional[str] = None,
                  common_region_id: Optional[str] = None) -> Dict[str, Any]:
    out = {"kind": kind, "bbox": bbox}
    if text is not None:
        out["text"] = text
    if common_region_id is not None:
        out["common_region_id"] = common_region_id
    return out


def page(number: int, *, common_regions=None, figures=None, tables=None) -> Dict[str, Any]:
    return {
        "page": number,
        "common_regions": list(common_regions or []),
        "figures": list(figures or []),
        "tables": list(tables or []),
    }


def case(case_id: str, pdf: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"case_id": case_id, "pdf": pdf, "pages": pages}


def build_manifest(cases: List[Dict[str, Any]], *, name: str = "picker_cmc", version: str = "dev",
                   mode: str = "detector") -> Dict[str, Any]:
    return {
        "schema_version": schema.SCHEMA_VERSION,
        "coordinate_unit": schema.COORDINATE_UNIT,
        "coordinate_origin": schema.COORDINATE_ORIGIN,
        "producer": {"name": name, "version": version, "mode": mode},
        "cases": cases,
    }


def write_manifest(path: Path | str, manifest: Dict[str, Any]) -> Path:
    validate_or_raise(manifest)  # never write a contract-invalid manifest
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
