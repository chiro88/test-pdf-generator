"""D25 post-edit artifact export.

Builds review overlays/crops from an editor-save-manifest-v0 — the human-edited
SAVED state is the source of truth (NOT a fresh detector run), so the artifacts
reflect the latest edited bboxes. The edit log is carried through to the summary.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from detector.review_artifacts import (
    _overlay_boxes_for_page, _render_crop, _render_overlay, _safe_index,
)

EXPORT_SCHEMA_VERSION = "edited-review-v0"


class ExportError(Exception):
    pass


def export_artifacts(manifest: Dict[str, Any], out_dir: str | Path, *,
                     scale: float = 2.0, crop_scale: float = 3.0) -> Dict[str, Any]:
    """Render per-page overlays + figure/table body crops from the SAVED manifest."""
    out_dir = Path(out_dir)
    pdf = manifest.get("source_pdf", "")
    if not pdf or not Path(pdf).exists():
        raise ExportError(f"source_pdf not resolvable: {pdf!r}")
    out_dir.mkdir(parents=True, exist_ok=True)

    page_records: List[Dict[str, Any]] = []
    crop_records: List[Dict[str, Any]] = []
    for page in manifest.get("pages", []):
        pno = page.get("page")
        overlay_rel = f"pages/page_{pno:03d}_overlay.png"
        _render_overlay(pdf, pno, _overlay_boxes_for_page(page), scale, out_dir / overlay_rel)
        page_records.append({"page": pno, "overlay": overlay_rel,
                             "figures": len(page.get("figures", [])), "tables": len(page.get("tables", []))})
        for kind, items in (("figure", page.get("figures", [])), ("table", page.get("tables", []))):
            for obj in items:
                crop_rel = f"crops/{kind}_{_safe_index(obj.get('index', 'x'))}_body_region.png"
                ok = _render_crop(pdf, pno, obj.get("body_region"), crop_scale, out_dir / crop_rel)
                crop_records.append({"page": pno, "kind": kind, "index": obj.get("index"),
                                     "crop": crop_rel if ok else None, "body_region": obj.get("body_region")})

    summary = {
        "ok": True,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "source_manifest_schema": manifest.get("schema_version"),
        "source_pdf": pdf,
        "pages": len(manifest.get("pages", [])),
        "edit_count": len(manifest.get("edits", [])),
        "figures": sum(p["figures"] for p in page_records),
        "tables": sum(p["tables"] for p in page_records),
        "artifacts": {
            "index": "index.md",
            "pages": [r["overlay"] for r in page_records],
            "crops": [c["crop"] for c in crop_records if c["crop"]],
        },
        "objects": crop_records,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_index(out_dir, manifest, page_records, crop_records)
    return summary


def _write_index(out_dir: Path, manifest, page_records, crop_records) -> None:
    lines = [f"# Edited review export — `{Path(manifest.get('source_pdf', '')).name}`", ""]
    lines.append("> Built from the **edited** editor-save-manifest-v0 (post-correction), "
                 f"with {len(manifest.get('edits', []))} edit(s) applied.")
    lines.append("")
    lines.append("| page | overlay | figures | tables |")
    lines.append("|---|---|---|---|")
    for r in page_records:
        lines.append(f"| {r['page']} | [overlay]({r['overlay']}) | {r['figures']} | {r['tables']} |")
    lines.append("")
    lines.append("## Figure / table body crops (edited bboxes)")
    lines.append("")
    lines.append("| page | type | index | body_region | crop |")
    lines.append("|---|---|---|---|---|")
    for c in crop_records:
        crop = f"[crop]({c['crop']})" if c.get("crop") else "—"
        lines.append(f"| {c['page']} | {c['kind']} | {c.get('index','')} | {c.get('body_region')} | {crop} |")
    (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
