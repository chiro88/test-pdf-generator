"""downstream-package-v0 validator (D27)."""
from __future__ import annotations

from typing import Any, List

from . import schema


class DownstreamPackageError(Exception):
    pass


def _is_bbox(v: Any) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 4
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def validate_package(data: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["package root must be an object"]
    if data.get("schema_version") != schema.SCHEMA_VERSION:
        errors.append(f"schema_version must be {schema.SCHEMA_VERSION!r}")
    if data.get("coordinate_unit") != schema.COORDINATE_UNIT:
        errors.append(f"coordinate_unit must be {schema.COORDINATE_UNIT!r}")
    if data.get("coordinate_origin") != schema.COORDINATE_ORIGIN:
        errors.append(f"coordinate_origin must be {schema.COORDINATE_ORIGIN!r}")
    for f in ("source_pdf", "source_editor_manifest"):
        if not isinstance(data.get(f), str) or not data.get(f):
            errors.append(f"{f} must be a non-empty string")
    objs = data.get("objects")
    if not isinstance(objs, list):
        errors.append("objects must be a list")
        return errors
    for i, o in enumerate(objs):
        op = f"objects[{i}]"
        if not isinstance(o, dict):
            errors.append(f"{op} must be an object")
            continue
        if not isinstance(o.get("object_id"), str) or not o.get("object_id"):
            errors.append(f"{op}.object_id must be a non-empty string")
        if o.get("kind") not in schema.KINDS:
            errors.append(f"{op}.kind must be one of {schema.KINDS}")
        if not isinstance(o.get("page"), int):
            errors.append(f"{op}.page must be an integer")
        for r in ("caption_region", "body_region"):
            if not _is_bbox(o.get(r)):
                errors.append(f"{op}.{r} must be 4 numbers")
        if "context_region" in o and o["context_region"] is not None and not _is_bbox(o["context_region"]):
            errors.append(f"{op}.context_region must be 4 numbers when present")
        if not isinstance(o.get("crops"), dict):
            errors.append(f"{op}.crops must be an object")
        if not o.get("downstream_task_hint"):
            errors.append(f"{op}.downstream_task_hint is required")
    return errors


def validate_or_raise(data: Any) -> None:
    errors = validate_package(data)
    if errors:
        raise DownstreamPackageError("downstream-package-v0 invalid:\n" + "\n".join(errors))
