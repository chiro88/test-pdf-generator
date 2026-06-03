"""editor-save-manifest-v0 builder (D22).

Turns a detector-output-v0 manifest (the initial PROPOSAL) into an
editor-save-manifest (the human-corrected candidate), and records operator edits
as an append-only log alongside the in-place region values.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from . import schema
from .validator import validate_or_raise


def build_initial(detector_manifest: Dict[str, Any], *, source_pdf: str,
                  source_detector_manifest: str) -> Dict[str, Any]:
    """A save manifest pre-loaded from the detector proposal, with an empty edit log."""
    pages: List[Dict[str, Any]] = []
    for case in detector_manifest.get("cases", []):
        for page in case.get("pages", []):
            pages.append({
                "page": page.get("page"),
                "figures": list(page.get("figures", [])),
                "tables": list(page.get("tables", [])),
                "common_regions": list(page.get("common_regions", [])),
            })
    return {
        "schema_version": schema.SCHEMA_VERSION,
        "source_pdf": source_pdf,
        "source_detector_manifest": source_detector_manifest,
        "coordinate_unit": schema.COORDINATE_UNIT,
        "coordinate_origin": schema.COORDINATE_ORIGIN,
        "pages": pages,
        "edits": [],
    }


def _find_object(manifest: Dict[str, Any], object_id: str):
    kind, index, page_tag = object_id.split(":")
    page_no = int(page_tag.replace("page", ""))
    bucket = "figures" if kind == "figure" else "tables"
    for page in manifest["pages"]:
        if page.get("page") != page_no:
            continue
        for obj in page.get(bucket, []):
            if obj.get("index") == index:
                return obj
    return None


def apply_bbox_edit(manifest: Dict[str, Any], object_id: str, region: str,
                    after: List[float]) -> Dict[str, Any]:
    """Move/resize a region of an existing object, appending to the edit log."""
    obj = _find_object(manifest, object_id)
    before = list(obj.get(region)) if obj and obj.get(region) is not None else None
    if obj is not None:
        obj[region] = list(after)
    manifest.setdefault("edits", []).append({
        "object_id": object_id, "operation": "update_bbox", "region": region,
        "before": before, "after": list(after),
    })
    return manifest


def write_manifest(path: Path | str, manifest: Dict[str, Any]) -> Path:
    validate_or_raise(manifest)            # never write an invalid save manifest
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
