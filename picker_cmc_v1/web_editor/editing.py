"""D24 web-editor edit/save operations (server side).

bbox edits mutate the in-memory editor-save-manifest AND append to its edit log;
Save / Save-As validate before writing and keep Save-As within the run directory
(path-traversal guard). Ruler is client-side only and is never persisted.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from editor_manifest import schema as em_schema
from editor_manifest.writer import write_manifest
from .models import RunContext

EDIT_ERROR_CODES = (
    "EDIT_OBJECT_NOT_FOUND", "EDIT_REGION_NOT_FOUND", "EDIT_BAD_BBOX",
    "EDIT_OUT_OF_PAGE_BOUNDS", "SAVE_MANIFEST_INVALID", "SAVE_PATH_NOT_ALLOWED",
    "SAVE_WRITE_FAILED",
)

_FIG_TBL_REGIONS = ("caption_region", "body_region", "context_region")


class EditError(Exception):
    def __init__(self, code: str, message: str, field: Optional[str] = None):
        assert code in EDIT_ERROR_CODES, f"unknown edit error code {code!r}"
        self.code = code
        self.message = message
        self.field = field
        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> dict:
        out = {"ok": False, "error_code": self.code, "message": self.message}
        if self.field:
            out["field"] = self.field
        return out


def _is_bbox(v: Any) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 4
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def _live_object(manifest: Dict[str, Any], object_id: str) -> Optional[Tuple[int, str, Dict[str, Any]]]:
    """Return (page, kind, live-object-ref) — the actual object inside the manifest."""
    parts = object_id.split(":")
    if len(parts) < 3:
        return None
    kind, ident, page_tag = parts[0], ":".join(parts[1:-1]), parts[-1]
    try:
        page = int(page_tag.replace("page", ""))
    except ValueError:
        return None
    for p in manifest.get("pages", []):
        if p.get("page") != page:
            continue
        if kind in ("figure", "table"):
            for o in p.get(kind + "s", []):
                if str(o.get("index")) == ident:
                    return page, kind, o
        elif kind == "common":
            for c in p.get("common_regions", []):
                rid = c.get("common_region_id") or c.get("kind")
                if str(rid) == ident:
                    return page, "common", c
    return None


def edit_bbox(ctx: RunContext, object_id: str, region: str, bbox: List[float]) -> Dict[str, Any]:
    """Validate + apply a bbox edit in memory; append to the edit log. Raises EditError."""
    found = _live_object(ctx.manifest, object_id)
    if found is None:
        raise EditError("EDIT_OBJECT_NOT_FOUND", f"object_id not found: {object_id}", field="object_id")
    page, kind, obj = found

    valid_regions = ("bbox",) if kind == "common" else _FIG_TBL_REGIONS
    if region not in valid_regions:
        raise EditError("EDIT_REGION_NOT_FOUND",
                        f"region {region!r} invalid for {kind} (allowed: {valid_regions})", field="region")
    if not _is_bbox(bbox):
        raise EditError("EDIT_BAD_BBOX", "bbox must be 4 numbers", field="bbox")
    x0, y0, x1, y1 = bbox
    if not (x0 < x1 and y0 < y1):
        raise EditError("EDIT_BAD_BBOX", "bbox requires x0 < x1 and y0 < y1", field="bbox")
    size = ctx.page_sizes.get(page)
    if size:
        w, h = size
        if x0 < -0.5 or y0 < -0.5 or x1 > w + 0.5 or y1 > h + 0.5:
            raise EditError("EDIT_OUT_OF_PAGE_BOUNDS",
                            f"bbox outside page bounds (page {w:.0f}x{h:.0f})", field="bbox")

    before = list(obj.get(region)) if obj.get(region) is not None else None
    obj[region] = [round(float(c), 2) for c in bbox]
    ctx.manifest.setdefault("edits", []).append({
        "object_id": object_id, "operation": "update_bbox", "region": region,
        "before": before, "after": obj[region],
    })
    ctx.dirty = True
    return {"ok": True, "object_id": object_id, "region": region,
            "before": before, "after": obj[region], "dirty": True}


def save(ctx: RunContext) -> Dict[str, Any]:
    """Overwrite the run's editor_save_manifest.json (validate first)."""
    try:
        write_manifest(ctx.save_path, ctx.manifest)          # validates on write
    except Exception as exc:
        if "invalid" in str(exc).lower():
            raise EditError("SAVE_MANIFEST_INVALID", str(exc))
        raise EditError("SAVE_WRITE_FAILED", str(exc))
    ctx.dirty = False
    return {"ok": True, "saved": str(ctx.save_path), "dirty": False,
            "edit_count": len(ctx.manifest.get("edits", []))}


def save_as(ctx: RunContext, rel_path: str) -> Dict[str, Any]:
    """Write the manifest to a path UNDER the run directory (traversal guard)."""
    run_root = ctx.run_dir.resolve()
    target = (ctx.run_dir / rel_path).resolve()
    if run_root != target and run_root not in target.parents:
        raise EditError("SAVE_PATH_NOT_ALLOWED",
                        f"save-as path must be inside the run directory: {rel_path}", field="path")
    try:
        write_manifest(target, ctx.manifest)
    except Exception as exc:
        if "invalid" in str(exc).lower():
            raise EditError("SAVE_MANIFEST_INVALID", str(exc))
        raise EditError("SAVE_WRITE_FAILED", str(exc))
    ctx.dirty = False
    return {"ok": True, "saved": str(target), "dirty": False,
            "edit_count": len(ctx.manifest.get("edits", []))}


def edit_state(ctx: RunContext) -> Dict[str, Any]:
    return {"ok": True, "dirty": ctx.dirty,
            "edit_count": len(ctx.manifest.get("edits", [])),
            "save_path": str(ctx.save_path)}
