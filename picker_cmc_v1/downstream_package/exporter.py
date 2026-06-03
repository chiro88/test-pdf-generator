"""downstream-package-v0 exporter (D27).

Builds a per-object package (crops + metadata JSON + JSONL + index) from an
editor-save-manifest-v0 — the human-EDITED bboxes are the source of truth. No
content interpretation, no LLM calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from detector.review_artifacts import _render_crop, _safe_index

from . import schema
from .validator import validate_or_raise


class ExportError(Exception):
    pass


def _object_id(kind: str, index: str, page: int) -> str:
    return f"{kind}:{index}:page{page}"


def build_package(manifest: Dict[str, Any], out_dir: str | Path, *, crop_scale: float = 3.0) -> Dict[str, Any]:
    """Export figures/tables from a saved manifest into a downstream package."""
    out_dir = Path(out_dir)
    pdf = manifest.get("source_pdf", "")
    if not pdf or not Path(pdf).exists():
        raise ExportError(f"source_pdf not resolvable: {pdf!r}")
    out_dir.mkdir(parents=True, exist_ok=True)

    objects: List[Dict[str, Any]] = []
    for page in manifest.get("pages", []):
        pno = page.get("page")
        for kind in ("figure", "table"):
            for obj in page.get(kind + "s", []):
                index = obj.get("index")
                crops: Dict[str, str] = {}
                for region in schema.REGIONS:
                    bbox = obj.get(f"{region}_region")
                    if not bbox:
                        continue
                    rel = f"crops/{kind}_{_safe_index(index)}_{region}.png"
                    if _render_crop(pdf, pno, bbox, crop_scale, out_dir / rel):
                        crops[region] = rel
                objects.append({
                    "object_id": _object_id(kind, index, pno),
                    "kind": kind, "page": pno, "index": index, "title": obj.get("title"),
                    "caption_region": obj.get("caption_region"),
                    "body_region": obj.get("body_region"),
                    "context_region": obj.get("context_region"),
                    "crops": crops,
                    "downstream_task_hint": schema.TASK_HINTS.get(kind, "unknown"),
                })

    package = {
        "schema_version": schema.SCHEMA_VERSION,
        "source_pdf": pdf,
        "source_editor_manifest": manifest.get("source_detector_manifest", ""),
        "coordinate_unit": schema.COORDINATE_UNIT,
        "coordinate_origin": schema.COORDINATE_ORIGIN,
        "objects": objects,
    }
    validate_or_raise(package)
    (out_dir / "package_manifest.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out_dir / "objects.jsonl").open("w", encoding="utf-8") as f:
        for o in objects:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    _write_index(out_dir, package)
    return {"ok": True, "schema_version": schema.SCHEMA_VERSION, "objects": len(objects),
            "figures": sum(1 for o in objects if o["kind"] == "figure"),
            "tables": sum(1 for o in objects if o["kind"] == "table"),
            "crops": sum(len(o["crops"]) for o in objects),
            "package_manifest": str(out_dir / "package_manifest.json"),
            "objects_jsonl": str(out_dir / "objects.jsonl")}


def _write_index(out_dir: Path, package: Dict[str, Any]) -> None:
    lines = [f"# Downstream object package — `{Path(package['source_pdf']).name}`", ""]
    lines.append("> `downstream-package-v0` from the edited editor-save-manifest. "
                 "Geometry + crops only; no content interpretation.")
    lines.append("")
    lines.append("| object_id | kind | page | title | hint | crops |")
    lines.append("|---|---|---|---|---|---|")
    for o in package["objects"]:
        crops = ", ".join(f"[{r}]({p})" for r, p in o["crops"].items()) or "—"
        title = (o.get("title") or "").replace("|", "\\|")
        lines.append(f"| `{o['object_id']}` | {o['kind']} | {o['page']} | {title} | {o['downstream_task_hint']} | {crops} |")
    (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
