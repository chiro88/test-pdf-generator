"""D17: real-PDF operator review harness (no truth, no compare).

Runs the no-truth detector on an arbitrary user PDF and produces a human-review
package: a contract-valid detector-output-v0 manifest, per-page overlay PNGs
(detector regions drawn on the rendered page), figure/table body crops, a
``review_index.md`` an operator can read directly, and a ``summary.json``.

This makes NO correctness claim: there is no ground truth for a real PDF, so the
result is a visual review artifact, not a pass/fail. Nothing here is
case-specific — it only draws what ``detect_pdf`` returns.

Coordinates are PDF points, top-left origin throughout (PyMuPDF page space is
also top-left); boxes are drawn directly and rendered at ``scale``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz

from detector_output import writer

from .pipeline import detect_pdf
from .review_feedback import build_review_template, object_id_for

REVIEW_SCHEMA_VERSION = "rtm-review-v0"

# Region colors (RGB 0..1).
FIG_COLOR = (0.0, 0.0, 0.9)
TBL_COLOR = (0.0, 0.6, 0.0)
HF_COLOR = (0.45, 0.45, 0.45)
WM_COLOR = (0.95, 0.55, 0.0)
_BODY_W = 2.4
_AUX_W = 1.2
_DASH = "[3 3] 0"


class ReviewInputError(Exception):
    """Raised when the input PDF cannot be opened/processed."""


def _safe_index(index: str) -> str:
    """'3.3' -> '3-3' for filesystem-safe crop names."""
    return "".join(c if c.isalnum() else "-" for c in str(index)).strip("-") or "x"


def _draw_box(page: "fitz.Page", bbox, color, width, label: Optional[str], *, dashed: bool = False) -> None:
    if not bbox:
        return
    page.draw_rect(fitz.Rect(*bbox), color=color, width=width, dashes=(_DASH if dashed else None))
    if label:
        ly = bbox[1] - 2 if bbox[1] > 10 else bbox[3] + 9
        page.insert_text((bbox[0] + 1, ly), label, fontsize=7, color=color)


def _overlay_boxes_for_page(page_out: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All draw instructions for one detector-output page."""
    boxes: List[Dict[str, Any]] = []
    for fig in page_out.get("figures", []):
        tag = f"FIG {fig.get('index', '')}"
        boxes.append({"bbox": fig["body_region"], "color": FIG_COLOR, "width": _BODY_W, "label": f"[{tag}] body"})
        boxes.append({"bbox": fig["caption_region"], "color": FIG_COLOR, "width": _AUX_W, "label": f"[{tag}] caption", "dashed": True})
        boxes.append({"bbox": fig.get("context_region"), "color": FIG_COLOR, "width": _AUX_W, "label": None, "dashed": True})
    for tbl in page_out.get("tables", []):
        tag = f"TBL {tbl.get('index', '')}"
        boxes.append({"bbox": tbl["body_region"], "color": TBL_COLOR, "width": _BODY_W, "label": f"[{tag}] body"})
        boxes.append({"bbox": tbl["caption_region"], "color": TBL_COLOR, "width": _AUX_W, "label": f"[{tag}] caption", "dashed": True})
        boxes.append({"bbox": tbl.get("context_region"), "color": TBL_COLOR, "width": _AUX_W, "label": None, "dashed": True})
    for cr in page_out.get("common_regions", []):
        kind = cr.get("kind")
        color = WM_COLOR if kind == "watermark" else HF_COLOR
        boxes.append({"bbox": cr["bbox"], "color": color, "width": _AUX_W, "label": f"[{kind[:2].upper()}]"})
    return boxes


def _render_overlay(pdf_path: Path, page_no: int, boxes: List[Dict[str, Any]], scale: float, out_png: Path) -> None:
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_no - 1]
        for b in boxes:
            _draw_box(page, b.get("bbox"), b["color"], b["width"], b.get("label"), dashed=b.get("dashed", False))
        out_png.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(str(out_png))
    finally:
        doc.close()


def _render_crop(pdf_path: Path, page_no: int, bbox, scale: float, out_png: Path) -> bool:
    if not bbox:
        return False
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_no - 1]
        clip = fitz.Rect(*bbox) & page.rect           # keep within the page
        if clip.is_empty or clip.width <= 1 or clip.height <= 1:
            return False
        out_png.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False).save(str(out_png))
        return True
    finally:
        doc.close()


def build_review_package(pdf_path: str | Path, out_dir: str | Path, *, name: Optional[str] = None,
                         scale: float = 2.0, crops: bool = True, crop_scale: float = 3.0) -> Dict[str, Any]:
    """Detect on one real PDF and write the operator review package.

    Returns the summary dict (also written as summary.json). Raises
    ReviewInputError if the PDF cannot be opened.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    if not pdf_path.exists():
        raise ReviewInputError(f"PDF not found: {pdf_path}")
    try:
        probe = fitz.open(str(pdf_path))
        page_count = probe.page_count
        probe.close()
    except Exception as exc:                          # not a readable PDF
        raise ReviewInputError(f"cannot open PDF {pdf_path}: {exc}") from exc

    name = name or pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    detection = detect_pdf(pdf_path)                  # {"pages": [...]} — never reads truth
    pages = detection["pages"]

    # Contract-valid detector-output-v0 manifest (validated on write).
    manifest = writer.build_manifest([writer.case(name, str(pdf_path), pages)], name="picker_cmc", mode="detector")
    manifest_path = writer.write_manifest(out_dir / "detected_manifest.json", manifest)

    warnings: List[str] = []
    figures_detected = sum(len(p.get("figures", [])) for p in pages)
    tables_detected = sum(len(p.get("tables", [])) for p in pages)
    commons_detected = sum(len(p.get("common_regions", [])) for p in pages)
    watermarks_detected = sum(1 for p in pages for c in p.get("common_regions", []) if c.get("kind") == "watermark")
    if figures_detected == 0 and tables_detected == 0:
        warnings.append("no figures or tables detected — verify this PDF has captioned figures/tables")

    # Per-page overlays + per-object crops.
    page_records: List[Dict[str, Any]] = []
    crop_records: List[Dict[str, Any]] = []
    for p in pages:
        pno = p["page"]
        overlay_rel = f"pages/page_{pno:03d}_overlay.png"
        _render_overlay(pdf_path, pno, _overlay_boxes_for_page(p), scale, out_dir / overlay_rel)
        page_records.append({"page": pno, "overlay": overlay_rel,
                             "figures": len(p.get("figures", [])), "tables": len(p.get("tables", [])),
                             "common_regions": len(p.get("common_regions", []))})
        if not crops:
            continue
        for kind, items in (("figure", p.get("figures", [])), ("table", p.get("tables", []))):
            for obj in items:
                crop_rel = f"crops/{kind}_{_safe_index(obj.get('index', 'x'))}_body.png"
                ok = _render_crop(pdf_path, pno, obj.get("body_region"), crop_scale, out_dir / crop_rel)
                crop_records.append({"page": pno, "kind": kind, "index": obj.get("index"),
                                     "object_id": object_id_for(kind, obj.get("index"), pno),
                                     "title": obj.get("title"), "crop": crop_rel if ok else None,
                                     "caption_region": obj.get("caption_region"), "body_region": obj.get("body_region"),
                                     "context_region": obj.get("context_region"),
                                     "table_group_id": obj.get("table_group_id")})

    review_index = _write_review_index(out_dir, pdf_path, page_count, page_records, crop_records, warnings)

    # D19: a pre-filled operator review template (every object -> decision: accept),
    # ready for a reviewer to edit and feed to summarize_review_feedback.py.
    template = build_review_template(pages, pdf_path.name)
    try:
        import yaml
        (out_dir / "review_result.template.yaml").write_text(
            yaml.safe_dump(template, sort_keys=False, allow_unicode=True), encoding="utf-8")
        template_rel = "review_result.template.yaml"
    except Exception:
        (out_dir / "review_result.template.json").write_text(
            json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        template_rel = "review_result.template.json"

    summary = {
        "ok": True,
        "schema_version": REVIEW_SCHEMA_VERSION,
        "pdf": str(pdf_path),
        "name": name,
        "pages": page_count,
        "figures_detected": figures_detected,
        "tables_detected": tables_detected,
        "common_regions_detected": commons_detected,
        "watermarks_detected": watermarks_detected,
        "artifacts": {
            "manifest": str(manifest_path.relative_to(out_dir)),
            "review_index": str(Path(review_index).relative_to(out_dir)),
            "review_template": template_rel,
            "pages": [r["overlay"] for r in page_records],
            "crops": [c["crop"] for c in crop_records if c["crop"]],
        },
        "warnings": warnings,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _write_review_index(out_dir: Path, pdf_path: Path, page_count: int, page_records, crop_records, warnings) -> str:
    lines: List[str] = []
    lines.append(f"# Detector review — `{pdf_path.name}`")
    lines.append("")
    lines.append("> No ground truth exists for a real PDF: this is a **visual review** package, "
                 "NOT a correctness pass. An operator must confirm each figure/table band.")
    lines.append("")
    lines.append(f"- **PDF**: `{pdf_path}`")
    lines.append(f"- **Pages**: {page_count}")
    lines.append(f"- **Figures detected**: {sum(r['figures'] for r in page_records)}")
    lines.append(f"- **Tables detected**: {sum(r['tables'] for r in page_records)}")
    lines.append("")
    lines.append("## Pages")
    lines.append("")
    lines.append("| page | overlay | figures | tables | common regions |")
    lines.append("|---|---|---|---|---|")
    for r in page_records:
        lines.append(f"| {r['page']} | [overlay]({r['overlay']}) | {r['figures']} | {r['tables']} | {r['common_regions']} |")
    lines.append("")
    lines.append("## Detected figures / tables")
    lines.append("")
    if not crop_records:
        lines.append("_None detected._")
    else:
        lines.append("Operator: copy `review_result.template.yaml`, set each `decision` "
                     "(accept / bad_body_region / false_positive / …), then run "
                     "`summarize_review_feedback.py`.")
        lines.append("")
        lines.append("| object_id | page | type | index | title | caption_region | body_region | context_region | crop | decision |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for c in crop_records:
            crop = f"[crop]({c['crop']})" if c.get("crop") else "—"
            title = (c.get("title") or "").replace("|", "\\|")
            lines.append(f"| `{c.get('object_id','')}` | {c['page']} | {c['kind']} | {c.get('index','')} | {title} | "
                         f"{c.get('caption_region')} | {c.get('body_region')} | {c.get('context_region')} | {crop} | _(accept?)_ |")
    lines.append("")
    lines.append("## Warnings / known limitations")
    lines.append("")
    lines.append("- No ground truth for a real PDF — visual review only; no pass/fail.")
    lines.append("- Rotated / morph / image-like watermarks may extract unreliably (reported, never silently skipped).")
    lines.append("- Structure/geometry only — no semantic field extraction.")
    for w in warnings:
        lines.append(f"- ⚠️ {w}")
    path = out_dir / "review_index.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
