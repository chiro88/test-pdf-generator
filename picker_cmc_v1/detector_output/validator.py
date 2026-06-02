"""detector-output-v0 validator (D10).

Structural contract check only — it does NOT judge detector correctness, only
that the manifest is well-formed and compare-compatible.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import schema


class DetectorOutputError(Exception):
    """Raised when a detector-output manifest violates the contract."""


def _is_bbox(v: Any) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 4
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def validate_manifest(data: Any) -> List[str]:
    """Return a list of contract violations (empty list == valid)."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be an object"]

    if data.get("schema_version") != schema.SCHEMA_VERSION:
        errors.append(f"schema_version must be {schema.SCHEMA_VERSION!r} (got {data.get('schema_version')!r})")
    if data.get("coordinate_unit") != schema.COORDINATE_UNIT:
        errors.append(f"coordinate_unit must be {schema.COORDINATE_UNIT!r} (got {data.get('coordinate_unit')!r})")
    if data.get("coordinate_origin") != schema.COORDINATE_ORIGIN:
        errors.append(f"coordinate_origin must be {schema.COORDINATE_ORIGIN!r} (got {data.get('coordinate_origin')!r})")

    producer = data.get("producer")
    if not isinstance(producer, dict):
        errors.append("producer object is required")
    else:
        for f in schema.PRODUCER_FIELDS:
            if not producer.get(f):
                errors.append(f"producer.{f} is required")

    cases = data.get("cases")
    if not isinstance(cases, list):
        errors.append("cases must be a list")
        return errors

    for ci, case in enumerate(cases):
        cp = f"cases[{ci}]"
        if not isinstance(case, dict):
            errors.append(f"{cp} must be an object")
            continue
        if not isinstance(case.get("case_id"), str) or not case["case_id"]:
            errors.append(f"{cp}.case_id must be a non-empty string")
        if not isinstance(case.get("pdf"), str) or not case["pdf"]:
            errors.append(f"{cp}.pdf must be a non-empty string")
        pages = case.get("pages")
        if not isinstance(pages, list):
            errors.append(f"{cp}.pages must be a list")
            continue
        for page in pages:
            pp = f"{cp}.page[{page.get('page') if isinstance(page, dict) else '?'}]"
            if not isinstance(page, dict) or not isinstance(page.get("page"), int):
                errors.append(f"{pp}.page must be an integer")
                continue
            for key in ("common_regions", "figures", "tables"):
                if not isinstance(page.get(key, []), list):
                    errors.append(f"{pp}.{key} must be a list")
            for ri, reg in enumerate(page.get("common_regions", []) or []):
                if reg.get("kind") not in schema.COMMON_KINDS:
                    errors.append(f"{pp}.common_regions[{ri}].kind must be one of {schema.COMMON_KINDS}")
                if not _is_bbox(reg.get("bbox")):
                    errors.append(f"{pp}.common_regions[{ri}].bbox must be 4 numbers")
            for fi, fig in enumerate(page.get("figures", []) or []):
                fp = f"{pp}.figures[{fi}]"
                if fig.get("kind") != "figure":
                    errors.append(f"{fp}.kind must be 'figure'")
                for f in schema.FIGURE_FIELDS:
                    if f not in fig:
                        errors.append(f"{fp}.{f} is required")
                if fig.get("title_position") not in schema.TITLE_POSITIONS:
                    errors.append(f"{fp}.title_position must be one of {schema.TITLE_POSITIONS}")
                for r in schema.FIGURE_REGIONS:
                    if not _is_bbox(fig.get(r)):
                        errors.append(f"{fp}.{r} must be 4 numbers")
            for ti, tbl in enumerate(page.get("tables", []) or []):
                tp = f"{pp}.tables[{ti}]"
                if tbl.get("kind") != "table":
                    errors.append(f"{tp}.kind must be 'table'")
                for f in schema.TABLE_FIELDS:
                    if f not in tbl:
                        errors.append(f"{tp}.{f} is required")
                for r in ("caption_region", "body_region"):
                    if not _is_bbox(tbl.get(r)):
                        errors.append(f"{tp}.{r} must be 4 numbers")
                if "context_region" in tbl and tbl["context_region"] is not None and not _is_bbox(tbl["context_region"]):
                    errors.append(f"{tp}.context_region must be 4 numbers when present")
    return errors


def validate_or_raise(data: Any) -> None:
    errors = validate_manifest(data)
    if errors:
        raise DetectorOutputError("detector-output-v0 invalid:\n" + "\n".join(errors))
