"""D23 manifest -> view-model helpers (object trees, overlays, object lookup)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from detector.review_feedback import object_id_for

_FIG_TBL_REGIONS = ("caption_region", "body_region", "context_region")


def _common_object_id(c: Dict[str, Any], page: int) -> str:
    rid = c.get("common_region_id") or c.get("kind") or "region"
    return f"common:{rid}:page{page}"


def _with_id(o: Dict[str, Any], kind: str, page: int) -> Dict[str, Any]:
    d = dict(o)
    d["object_id"] = object_id_for(kind, o.get("index"), page)
    return d


def _page(manifest: Dict[str, Any], page: int) -> Optional[Dict[str, Any]]:
    return next((p for p in manifest.get("pages", []) if p.get("page") == page), None)


def page_objects(manifest: Dict[str, Any], page: int) -> Optional[Dict[str, Any]]:
    pg = _page(manifest, page)
    if pg is None:
        return None
    return {
        "page": page,
        "figures": [_with_id(f, "figure", page) for f in pg.get("figures", [])],
        "tables": [_with_id(t, "table", page) for t in pg.get("tables", [])],
        "common_regions": [{**c, "object_id": _common_object_id(c, page)} for c in pg.get("common_regions", [])],
    }


def overlays(manifest: Dict[str, Any], page: int) -> Optional[Dict[str, Any]]:
    po = page_objects(manifest, page)
    if po is None:
        return None
    boxes: List[Dict[str, Any]] = []
    for kind in ("figures", "tables"):
        for o in po[kind]:
            for region in _FIG_TBL_REGIONS:
                if o.get(region):
                    boxes.append({"object_id": o["object_id"], "kind": kind[:-1],
                                  "region": region, "bbox": o[region]})
    for c in po["common_regions"]:
        if c.get("bbox"):
            boxes.append({"object_id": c["object_id"], "kind": c.get("kind"),
                          "region": "bbox", "bbox": c["bbox"]})
    return {"page": page, "overlays": boxes}


def all_objects(manifest: Dict[str, Any]) -> Dict[str, Tuple[int, str, Dict[str, Any]]]:
    out: Dict[str, Tuple[int, str, Dict[str, Any]]] = {}
    for p in manifest.get("pages", []):
        po = page_objects(manifest, p.get("page"))
        if not po:
            continue
        for kind in ("figures", "tables", "common_regions"):
            for o in po[kind]:
                out[o["object_id"]] = (p.get("page"), kind, o)
    return out


def find_object(manifest: Dict[str, Any], object_id: str) -> Optional[Tuple[int, str, Dict[str, Any]]]:
    return all_objects(manifest).get(object_id)
