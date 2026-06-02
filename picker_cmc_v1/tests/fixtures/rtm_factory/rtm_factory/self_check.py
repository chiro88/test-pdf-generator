from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Tuple

import fitz

from .coverage import AXIS_REQUIREMENTS, min_count

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Core and negative scenarios that must be present by exact case_id.
CORE_NAMES = [
    "core_fixed_header_footer",
    "core_variable_subtitle_header",
    "core_fixed_watermark",
    "core_figure_caption_bottom",
    "core_figure_caption_top",
    "core_multipage_table_cont",
    "core_same_title_tables",
    "core_wide_diagram_xrange",
]
NEGATIVE_NAMES = [
    "neg_plain_text_only",
    "neg_false_figure_of_merit",
    "neg_false_see_table_above",
    "neg_caption_reference_only",
    "neg_false_table_reference",
    "neg_weak_partial_header",
]


def _bbox_ok(bbox, width: float, height: float) -> bool:
    return (
        isinstance(bbox, list)
        and len(bbox) == 4
        and 0 <= bbox[0] < bbox[2] <= width
        and 0 <= bbox[1] < bbox[3] <= height
    )


def _iter_region_bboxes(page: dict) -> Iterable[Tuple[str, list]]:
    for region in page.get("common_regions", []):
        yield region.get("kind", "common"), region["bbox"]
    for fig in page.get("figures", []):
        yield "figure.caption_region", fig["caption_region"]
        yield "figure.body_region", fig["body_region"]
        yield "figure.context_region", fig["context_region"]
    for tbl in page.get("tables", []):
        yield "table.caption_region", tbl["caption_region"]
        yield "table.body_region", tbl["body_region"]
        if "context_region" in tbl:
            yield "table.context_region", tbl["context_region"]


def _check_case(case_dir: Path) -> list[str]:
    errors: list[str] = []
    case_id = case_dir.name
    pdf_path = case_dir / f"{case_id}.pdf"
    truth_path = case_dir / f"{case_id}.truth.json"
    notes_path = case_dir / f"{case_id}.notes.md"
    if not pdf_path.exists():
        errors.append(f"{case_id}: missing PDF")
        return errors
    if not truth_path.exists():
        errors.append(f"{case_id}: missing truth.json")
        return errors
    if not notes_path.exists() or not notes_path.read_text(encoding="utf-8").strip():
        errors.append(f"{case_id}: missing or empty notes.md")

    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:  # pragma: no cover - diagnostic path
        errors.append(f"{case_id}: PDF open failed: {exc}")
        return errors
    if doc.page_count != len(truth.get("pages", [])):
        errors.append(f"{case_id}: page_count mismatch pdf={doc.page_count} truth={len(truth.get('pages', []))}")
    for i in range(doc.page_count):
        png_path = case_dir / f"{case_id}.p{i + 1:02d}.png"
        if not png_path.exists() or not png_path.read_bytes().startswith(PNG_MAGIC):
            errors.append(f"{case_id}: missing/bad png {png_path.name}")
    for page in truth.get("pages", []):
        width = page["width"]
        height = page["height"]
        for label, bbox in _iter_region_bboxes(page):
            if not _bbox_ok(bbox, width, height):
                errors.append(f"{case_id}: invalid bbox {label}={bbox} for {width}x{height}")
    # Coordinate convention sanity: any top common header should be in upper half.
    for page in truth.get("pages", []):
        for reg in page.get("common_regions", []):
            if reg.get("kind") == "header" and reg["bbox"][1] >= page["height"] / 2:
                errors.append(f"{case_id}: header is not top-left y convention? bbox={reg['bbox']}")
    doc.close()
    return errors


def run_self_check(gallery_dir: Path) -> None:
    manifest_path = gallery_dir / "MANIFEST.json"
    index_path = gallery_dir / "index.md"
    if not manifest_path.exists():
        raise AssertionError("MANIFEST.json missing")
    if not index_path.exists():
        raise AssertionError("index.md missing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_ids = [case["case_id"] for case in manifest.get("cases", [])]
    errors: list[str] = []
    for case_id in case_ids:
        errors.extend(_check_case(gallery_dir / case_id))

    index_text = index_path.read_text(encoding="utf-8")
    for required in ["realism 1-5", "keep/drop", "critique"]:
        if required not in index_text:
            errors.append(f"index.md missing evaluation column: {required}")
    for case_id in case_ids:
        if case_id not in index_text:
            errors.append(f"index.md missing case: {case_id}")

    # --- scenario count + exact-name presence (handoff T2.4 / T2.5) ----------
    negative_count = sum(1 for c in manifest.get("cases", []) if "negative" in c.get("axes", {}))
    core_count = sum(1 for c in manifest.get("cases", []) if "core" in c.get("axes", {}))
    if core_count < 8:
        errors.append(f"core scenario count too low: {core_count}")
    if negative_count < 5:
        errors.append(f"negative scenario count too low: {negative_count}")
    case_id_set = set(case_ids)
    for name in CORE_NAMES:
        if name not in case_id_set:
            errors.append(f"missing core scenario by name: {name}")
    for name in NEGATIVE_NAMES:
        if name not in case_id_set:
            errors.append(f"missing negative scenario by name: {name}")
    total_cases = len(case_ids)
    if not (30 <= total_cases <= 50):
        errors.append(f"total case count out of 30-50 range: {total_cases}")

    # --- axis coverage gate (handoff T1 / T2.3) ------------------------------
    # Recompute coverage independently from per-case coverage_tags in the
    # manifest rather than trusting the generator's own summary.
    tag_counts: Counter = Counter()
    for case in manifest.get("cases", []):
        for tag in case.get("coverage_tags", []):
            tag_counts[tag] += 1
    for group, values in AXIS_REQUIREMENTS.items():
        for value in values:
            tag = f"{group}:{value}"
            cnt = tag_counts.get(tag, 0)
            need = min_count(tag)
            if cnt < need:
                errors.append(f"axis coverage too low: {tag} = {cnt} (need >= {need})")

    # --- truth-level checks (handoff T2.2 / T2.6 / T2.7) ---------------------
    truths = {cid: json.loads((gallery_dir / cid / f"{cid}.truth.json").read_text(encoding="utf-8")) for cid in case_ids}

    diagonal_watermarks = 0
    alpha_index_cases = 0
    suffixes_seen = set()
    for cid, truth in truths.items():
        has_alpha = False
        for page in truth.get("pages", []):
            for reg in page.get("common_regions", []):
                if reg.get("kind") == "watermark" and reg.get("rotation_deg") not in (None, 0, 0.0):
                    diagonal_watermarks += 1
            for item in page.get("figures", []) + page.get("tables", []):
                if any(c.isalpha() for c in item.get("index", "")):
                    has_alpha = True
            for tbl in page.get("tables", []):
                if tbl.get("is_continuation") and tbl.get("continuation_marker"):
                    suffixes_seen.add(tbl["continuation_marker"])
        if has_alpha:
            alpha_index_cases += 1

    if diagonal_watermarks == 0:
        errors.append("no diagonal watermark present in truth JSON (T2.2): a rotated watermark must not be silently skipped")
    if alpha_index_cases < 2:
        errors.append(f"alpha index (A.1) appears in only {alpha_index_cases} case(s); need >= 2 (T2.6)")
    required_suffixes = {"(cont)", "(continued)", "continued", "Continued", "cont."}
    missing_suffixes = sorted(required_suffixes - suffixes_seen)
    if missing_suffixes:
        errors.append(f"missing continuation suffixes (T2.7): {missing_suffixes}")

    # --- coverage summary must be present in MANIFEST (T2.8) ------------------
    coverage = manifest.get("coverage_summary")
    if not coverage or "counts" not in coverage:
        errors.append("MANIFEST.json missing machine-readable coverage_summary (T2.8)")

    if errors:
        raise AssertionError("RTM factory self-check failed:\n" + "\n".join(errors))
