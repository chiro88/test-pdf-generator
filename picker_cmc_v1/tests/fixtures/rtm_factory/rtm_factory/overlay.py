"""Compare-result visualization (handoff T5 / D5).

Turns truth + detected + a D4 compare_report into human-reviewable overlay
PNGs and an index, so a reviewer can eyeball where a detector diverged from the
frozen truth. This is NOT a detector and does NOT run one — it only draws what
D4 already computed.

Coordinates stay top-left throughout: truth/detected bboxes are PDF points
[x0,y0,x1,y1] with y increasing downward, drawn directly via PyMuPDF (whose
page space is also top-left) and rendered at `scale`. No bottom-left flip.

Modular by design:
  OverlayConfig / OverlayPagePlan      — knobs + per-page work unit
  collect_overlay_pages()              — decide which case/pages to draw
  render_pdf_page()/draw_region_box()  — leaf drawing
  draw_object_overlay()                — object → boxes
  write_overlay_manifest()/_index()    — outputs
  generate()                           — orchestration (called by the thin CLI)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz

from .compare import InvalidInput, extract_objects, load_detected_manifest, load_truth_cases

OVERLAY_SCHEMA_VERSION = "rtm-overlay-v0"

# Fixed semantic colors (RGB 0..1).
GREEN = (0.0, 0.6, 0.0)    # truth
BLUE = (0.0, 0.0, 0.9)     # detected
RED = (0.85, 0.0, 0.0)     # failed / missing
ORANGE = (0.95, 0.55, 0.0)  # extra
NORMAL_W = 2.0
FAIL_W = 5.0
DASH = "[3 3] 0"           # detected drawn dashed


@dataclass
class OverlayConfig:
    scale: float = 1.5
    failures_only: bool = False
    all_cases: bool = False
    case_id_filter: Optional[str] = None
    pages_filter: Optional[List[int]] = None


@dataclass
class OverlayPagePlan:
    case_id: str
    pdf_path: Path
    page: int
    truth_objs: Dict[Any, Dict] = field(default_factory=dict)
    det_objs: Dict[Any, Dict] = field(default_factory=dict)
    failures: List[Dict] = field(default_factory=list)


def _label_prefix(obj: Dict) -> str:
    kind = obj["kind"]
    if kind == "figure":
        return f"[FIG {obj.get('index', '')}]"
    if kind == "table":
        gid = obj["fields"].get("table_group_id", "")
        part = obj["fields"].get("part_index", "")
        return f"[TBL {gid} p{part}]"
    return {"header": "[H]", "footer": "[F]", "watermark": "[WM]"}.get(kind, f"[{kind}]")


def draw_object_overlay(obj: Dict, *, color, width, dashes=None) -> List[Dict]:
    """Expand one object into per-region draw boxes."""
    prefix = _label_prefix(obj)
    boxes: List[Dict] = []
    for region_name, bbox in obj["regions"].items():
        if bbox is None:
            continue
        rn = region_name.replace("_region", "")
        label = prefix if region_name == "bbox" else f"{prefix} {rn}"
        boxes.append({"bbox": bbox, "color": color, "width": width, "dashes": dashes, "label": label})
    return boxes


def draw_region_box(page: "fitz.Page", box: Dict) -> None:
    rect = fitz.Rect(*box["bbox"])
    page.draw_rect(rect, color=box["color"], width=box["width"], dashes=box.get("dashes"))
    label = box.get("label")
    if label:
        ly = box["bbox"][1] - 2 if box["bbox"][1] > 10 else box["bbox"][3] + 9
        page.insert_text((box["bbox"][0] + 1, ly), label, fontsize=7, color=box["color"])


def pt_to_px(bbox: list, scale: float) -> list:
    """PDF-pt bbox → rendered-PNG pixel bbox (top-left preserved)."""
    return [round(c * scale, 2) for c in bbox]


def render_pdf_page(pdf_path: Path, page_no: int, boxes: List[Dict], scale: float, out_png: Path) -> int:
    """Render one PDF page with `boxes` drawn on it; return # boxes drawn."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_no - 1]
    for box in boxes:
        draw_region_box(page, box)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_png))
    doc.close()
    return len(boxes)


def collect_overlay_pages(truth_cases: Dict[str, Dict], detected: Dict[str, Dict],
                          compare_report: Dict, truth_root: Path, config: OverlayConfig) -> List[OverlayPagePlan]:
    has_failures = bool(compare_report.get("failures"))
    failures_by_cp: Dict[Tuple[str, int], List[Dict]] = {}
    for f in compare_report.get("failures", []):
        failures_by_cp.setdefault((f["case_id"], f["page"]), []).append(f)

    plans: List[OverlayPagePlan] = []
    for cid, truth in truth_cases.items():
        if config.case_id_filter and cid != config.case_id_filter:
            continue
        truth_objs = extract_objects(truth)
        det_objs = extract_objects(detected[cid]) if cid in detected else {}
        for page in truth.get("pages", []):
            pg = page["page"]
            if config.pages_filter and pg not in config.pages_filter:
                continue
            page_failures = failures_by_cp.get((cid, pg), [])
            want = config.all_cases or (page_failures if (config.failures_only or has_failures) else False)
            if not want:
                continue
            plans.append(OverlayPagePlan(
                case_id=cid,
                pdf_path=truth_root / cid / f"{cid}.pdf",
                page=pg,
                truth_objs={k: v for k, v in truth_objs.items() if v["page"] == pg},
                det_objs={k: v for k, v in det_objs.items() if v["page"] == pg},
                failures=page_failures,
            ))
    return plans


def _failure_boxes(plan: OverlayPagePlan) -> List[Dict]:
    boxes: List[Dict] = []
    for f in plan.failures:
        key = tuple(f["key"])
        if f["status"] == "missing" and key in plan.truth_objs:
            boxes += draw_object_overlay(plan.truth_objs[key], color=RED, width=FAIL_W)
        elif f["status"] == "extra" and key in plan.det_objs:
            boxes += draw_object_overlay(plan.det_objs[key], color=ORANGE, width=FAIL_W)
        else:
            for r in f.get("regions", []):
                if r["passed"]:
                    continue
                rn = r["region"].replace("_region", "")
                if r.get("expected"):
                    boxes.append({"bbox": r["expected"], "color": GREEN, "width": NORMAL_W, "label": f"truth {rn}"})
                if r.get("actual"):
                    boxes.append({"bbox": r["actual"], "color": RED, "width": FAIL_W, "label": f"det {rn} Δ{r['delta']}"})
                elif r.get("expected"):
                    boxes.append({"bbox": r["expected"], "color": RED, "width": FAIL_W, "label": f"missing {rn}"})
            to = plan.truth_objs.get(key)
            for ff in f.get("fields", []):
                if ff["passed"] or not to:
                    continue
                anchor = to["regions"].get("caption_region") or next(iter(to["regions"].values()), None)
                if anchor:
                    boxes.append({"bbox": anchor, "color": RED, "width": 3.0,
                                  "label": f"{ff['field']}: exp {ff['expected']} got {ff['actual']}"})
    return boxes


def write_overlay_manifest(out_dir: Path, sources: Dict[str, str], cases: List[Dict]) -> Path:
    manifest = {
        "schema_version": OVERLAY_SCHEMA_VERSION,
        "source_compare_report": sources["compare_report"],
        "source_truth_root": sources["truth_root"],
        "source_detected": sources["detected"],
        "cases": cases,
    }
    path = out_dir / "overlay_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_overlay_index(out_dir: Path, cases: List[Dict], has_failures: bool) -> Path:
    lines = ["# RTM compare overlay index", ""]
    if not cases:
        lines.append("No overlays generated " + ("(all comparisons passed; rerun with --all to render everything)." if not has_failures else "."))
    else:
        lines.append("| case_id | page | overlay | failure overlay | regions | failures |")
        lines.append("|---|---|---|---|---|---|")
        for c in cases:
            for p in c["pages"]:
                fail_link = f"[fail]({p['failure_png']})" if p.get("failure_png") else "—"
                lines.append(f"| `{c['case_id']}` | {p['page']} | [overlay]({p['overlay_png']}) | {fail_link} | {p['regions_drawn']} | {p['failures_drawn']} |")
    path = out_dir / "index.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate(truth_root: Path | str, detected_path: Path | str, compare_report_path: Path | str,
             out_dir: Path | str, config: OverlayConfig) -> Dict[str, Any]:
    truth_root = Path(truth_root)
    out_dir = Path(out_dir)
    compare_report = json.loads(Path(compare_report_path).read_text(encoding="utf-8"))
    truth_cases = load_truth_cases(truth_root, case_filter=config.case_id_filter)
    detected = load_detected_manifest(detected_path)

    plans = collect_overlay_pages(truth_cases, detected, compare_report, truth_root, config)

    by_case: Dict[str, List[Dict]] = {}
    for plan in plans:
        overlay_boxes = (draw_object_overlay_all(plan.truth_objs, GREEN, NORMAL_W, None)
                         + draw_object_overlay_all(plan.det_objs, BLUE, NORMAL_W, DASH))
        rel_dir = plan.case_id
        overlay_png = out_dir / rel_dir / f"page_{plan.page:03d}_overlay.png"
        regions_drawn = render_pdf_page(plan.pdf_path, plan.page, overlay_boxes, config.scale, overlay_png)

        failure_rel = None
        failures_drawn = 0
        if plan.failures:
            fboxes = _failure_boxes(plan)
            failure_png = out_dir / rel_dir / f"page_{plan.page:03d}_failures.png"
            failures_drawn = render_pdf_page(plan.pdf_path, plan.page, fboxes, config.scale, failure_png)
            failure_rel = f"{rel_dir}/{failure_png.name}"

        by_case.setdefault(plan.case_id, []).append({
            "page": plan.page,
            "overlay_png": f"{rel_dir}/{overlay_png.name}",
            "failure_png": failure_rel,
            "regions_drawn": regions_drawn,
            "failures_drawn": failures_drawn,
        })

    cases = [{"case_id": cid, "pages": pages} for cid, pages in by_case.items()]
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = {
        "compare_report": str(compare_report_path),
        "truth_root": str(truth_root),
        "detected": str(detected_path),
    }
    manifest_path = write_overlay_manifest(out_dir, sources, cases)
    index_path = write_overlay_index(out_dir, cases, bool(compare_report.get("failures")))
    return {"cases": cases, "manifest": str(manifest_path), "index": str(index_path),
            "pages_rendered": len(plans)}


def draw_object_overlay_all(objs: Dict[Any, Dict], color, width, dashes) -> List[Dict]:
    boxes: List[Dict] = []
    for obj in objs.values():
        boxes += draw_object_overlay(obj, color=color, width=width, dashes=dashes)
    return boxes
