"""editor-save-manifest-v0 validator (D22)."""
from __future__ import annotations

from typing import Any, Dict, List

from . import schema


class EditorManifestError(Exception):
    """Raised when an editor-save-manifest violates the contract."""


def _is_bbox(v: Any) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 4
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def validate_manifest(data: Any) -> List[str]:
    """Return a list of contract violations (empty == valid)."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be an object"]

    if data.get("schema_version") != schema.SCHEMA_VERSION:
        errors.append(f"schema_version must be {schema.SCHEMA_VERSION!r} (got {data.get('schema_version')!r})")
    if data.get("coordinate_unit") != schema.COORDINATE_UNIT:
        errors.append(f"coordinate_unit must be {schema.COORDINATE_UNIT!r} (got {data.get('coordinate_unit')!r})")
    if data.get("coordinate_origin") != schema.COORDINATE_ORIGIN:
        errors.append(f"coordinate_origin must be {schema.COORDINATE_ORIGIN!r} (got {data.get('coordinate_origin')!r})")
    if not isinstance(data.get("source_pdf"), str) or not data.get("source_pdf"):
        errors.append("source_pdf must be a non-empty string")
    if not isinstance(data.get("source_detector_manifest"), str) or not data.get("source_detector_manifest"):
        errors.append("source_detector_manifest must be a non-empty string")

    pages = data.get("pages")
    if not isinstance(pages, list):
        errors.append("pages must be a list")
    else:
        for i, p in enumerate(pages):
            if not isinstance(p, dict) or not isinstance(p.get("page"), int):
                errors.append(f"pages[{i}].page must be an integer")
                continue
            for key in ("figures", "tables", "common_regions"):
                if not isinstance(p.get(key, []), list):
                    errors.append(f"pages[{i}].{key} must be a list")

    edits = data.get("edits")
    if not isinstance(edits, list):
        errors.append("edits must be a list (append-only edit log)")
    else:
        for i, e in enumerate(edits):
            ep = f"edits[{i}]"
            if not isinstance(e, dict):
                errors.append(f"{ep} must be an object")
                continue
            if not isinstance(e.get("object_id"), str) or not e.get("object_id"):
                errors.append(f"{ep}.object_id must be a non-empty string")
            if e.get("operation") not in schema.OPERATIONS:
                errors.append(f"{ep}.operation must be one of {schema.OPERATIONS}")
            if e.get("operation") == "update_bbox":
                if e.get("region") not in schema.REGION_NAMES:
                    errors.append(f"{ep}.region must be one of {schema.REGION_NAMES}")
                if not _is_bbox(e.get("after")):
                    errors.append(f"{ep}.after must be 4 numbers")
                if "before" in e and e["before"] is not None and not _is_bbox(e["before"]):
                    errors.append(f"{ep}.before must be 4 numbers when present")
    return errors


def validate_or_raise(data: Any) -> None:
    errors = validate_manifest(data)
    if errors:
        raise EditorManifestError("editor-save-manifest-v0 invalid:\n" + "\n".join(errors))
