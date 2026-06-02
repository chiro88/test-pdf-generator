from __future__ import annotations

import json
import re
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


# --- D3.5: truth-region vs PDF text-extraction overlap -----------------------
# Lenient on purpose: extracted text bboxes jitter by font/rendering, so a
# region passes if any extracted span overlaps it (IoU>0, or a center inside
# the other, within a small tolerance). Rotated/morph watermarks extract
# unreliably and are skipped WITH a recorded reason (never silently).
TEXT_TOL = 3.0


def _spans(page) -> list[tuple[str, list]]:
    spans: list[tuple[str, list]] = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for sp in line.get("spans", []):
                txt = (sp.get("text") or "").strip()
                if txt:
                    spans.append((txt, list(sp["bbox"])))
    return spans


def _iou(a: list, b: list) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _center_in(box_inner: list, box_outer: list) -> bool:
    cx = (box_inner[0] + box_inner[2]) / 2
    cy = (box_inner[1] + box_inner[3]) / 2
    return box_outer[0] <= cx <= box_outer[2] and box_outer[1] <= cy <= box_outer[3]


def _y_overlap(a: list, b: list) -> bool:
    return min(a[3], b[3]) - max(a[1], b[1]) > 0


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _overlapping_spans(expected: list, spans: list[tuple[str, list]], need_y: bool = True):
    exp = [expected[0] - TEXT_TOL, expected[1] - TEXT_TOL, expected[2] + TEXT_TOL, expected[3] + TEXT_TOL]
    out = []
    for txt, sb in spans:
        if _iou(exp, sb) > 0 or _center_in(sb, exp) or _center_in(exp, sb):
            if (not need_y) or _y_overlap(exp, sb):
                out.append((txt, sb))
    return out


def _match_region(expected_bbox: list, expected_key: str, spans, need_y: bool = True):
    """Return (status, extracted_bbox_or_text). status in {ok, none, mismatch}.

    A region passes only if extracted text overlaps it AND the aggregated
    overlapping text contains the expected key (figure/table index, or the
    header/footer/watermark text). This rejects "overlaps unrelated filler
    prose" false positives while staying lenient on exact geometry/wrapping.
    """
    ov = _overlapping_spans(expected_bbox, spans, need_y=need_y)
    if not ov:
        return "none", None
    agg = _norm("".join(t for t, _ in ov))
    key = _norm(expected_key)
    if key and key in agg:
        return "ok", ov[0][1]
    return "mismatch", ("".join(t for t, _ in ov)).strip()[:60]


def check_text_overlap(gallery_dir: Path, case_ids: list[str]) -> tuple[list[str], dict]:
    """Verify each text-bearing truth region overlaps the right extracted text."""
    errors: list[str] = []
    report: dict = {"checked": 0, "passed": 0, "skipped": [], "failures": []}

    def record(status, cid, pg, kind, idx, region, expected_key, bbox, extracted):
        report["checked"] += 1
        if status == "ok":
            report["passed"] += 1
            return
        note = "no extracted text overlaps region" if status == "none" else f"overlapping text {extracted!r} lacks expected key"
        msg = (f"{cid} p{pg} {kind}{(' ' + idx) if idx else ''} {region}: {note}; "
               f"expected_key={expected_key!r} expected_bbox={bbox}")
        errors.append(msg)
        report["failures"].append(msg)

    for cid in case_ids:
        truth = json.loads((gallery_dir / cid / f"{cid}.truth.json").read_text(encoding="utf-8"))
        try:
            doc = fitz.open(str(gallery_dir / cid / f"{cid}.pdf"))
        except Exception as exc:  # pragma: no cover
            errors.append(f"{cid}: PDF open failed during text-overlap check: {exc}")
            continue
        for page in truth.get("pages", []):
            pg = page["page"]
            spans = _spans(doc[pg - 1])
            for reg in page.get("common_regions", []):
                kind = reg.get("kind")
                bbox = reg["bbox"]
                key = reg.get("text", "")
                if kind == "watermark":
                    rot = reg.get("rotation_deg") or 0
                    if abs(rot) > 0.01:
                        report["skipped"].append(
                            f"{cid} p{pg} watermark rot={rot}: rotated/morph text extracts unreliably — skipped")
                        continue
                status, extracted = _match_region(bbox, key, spans, need_y=True)
                record(status, cid, pg, kind, "", "text", key, bbox, extracted)
            for fig in page.get("figures", []):
                idx = fig.get("index", "")
                status, extracted = _match_region(fig["caption_region"], idx, spans, need_y=True)
                record(status, cid, pg, "figure", idx, "caption_region", idx, fig["caption_region"], extracted)
            for tbl in page.get("tables", []):
                idx = tbl.get("index", "")
                status, extracted = _match_region(tbl["caption_region"], idx, spans, need_y=True)
                record(status, cid, pg, "table", idx, "caption_region", idx, tbl["caption_region"], extracted)
        doc.close()
    return errors, report


_LINE = 12.0


def _check_layout_consistency(truths: dict) -> tuple[list[str], dict]:
    """D9 gates: title position/gap, sequence y-order, interstitial height,
    target↔target overlap. Strict; only intentional_overlap_stress is exempt.
    Returns (errors, per-gate counts)."""
    errs: list[str] = []
    counts = {
        "target_target_unintended_overlaps": 0,
        "sequence_order_failures": 0,
        "interstitial_line_count_failures": 0,
        "title_position_failures": 0,
        "title_gap_failures": 0,
        "checked": {"targets": 0, "interstitials": 0, "sequences": 0},
    }
    for cid, truth in truths.items():
        stress = bool(truth.get("intentional_overlap_stress"))
        for page in truth.get("pages", []):
            pg = page["page"]
            targets = list(page.get("figures", [])) + list(page.get("tables", []))
            # title position / gap consistency
            for obj in targets:
                cap, body = obj.get("caption_region"), obj.get("body_region")
                if not cap or not body:
                    continue
                counts["checked"]["targets"] += 1
                pos = obj.get("title_position")
                if pos == "above" and not (cap[1] <= body[1]):
                    counts["title_position_failures"] += 1
                    errs.append(f"{cid} p{pg} {obj.get('index')}: title_position=above but caption y0 {cap[1]} >= body y0 {body[1]}")
                if pos == "below" and not (cap[1] >= body[1]):
                    counts["title_position_failures"] += 1
                    errs.append(f"{cid} p{pg} {obj.get('index')}: title_position=below but caption y0 {cap[1]} <= body y0 {body[1]}")
                gap_pt = (cap[1] - body[3]) if pos == "below" else (body[1] - cap[3])
                actual = int(round(max(0.0, gap_pt) / _LINE))
                if actual != obj.get("title_body_gap_lines"):
                    counts["title_gap_failures"] += 1
                    errs.append(f"{cid} p{pg} {obj.get('index')}: title_body_gap_lines={obj.get('title_body_gap_lines')} but actual {actual}")
            # target ↔ target unintended overlap (caption/body across distinct objects)
            if not stress:
                boxes = []
                for obj in targets:
                    for r in ("caption_region", "body_region"):
                        if obj.get(r):
                            boxes.append((f"{obj.get('index')}.{r}", obj[r]))
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        if _iou(boxes[i][1], boxes[j][1]) > 0.0:
                            counts["target_target_unintended_overlaps"] += 1
                            errs.append(f"{cid} p{pg}: targets overlap {boxes[i][0]} vs {boxes[j][0]}")
            # interstitial line_count vs height
            for nt in page.get("non_target_text_regions", []):
                if nt.get("role") == "interstitial_text" and nt.get("line_count"):
                    counts["checked"]["interstitials"] += 1
                    h = nt["bbox"][3] - nt["bbox"][1]
                    if abs(h - nt["line_count"] * _LINE) > 2.0:
                        counts["interstitial_line_count_failures"] += 1
                        errs.append(f"{cid} p{pg}: interstitial line_count={nt['line_count']} but height {h:.1f} != {nt['line_count'] * _LINE}")
        # layout_sequence order vs actual y order
        seq = truth.get("layout_sequence", [])
        if seq:
            counts["checked"]["sequences"] += 1
        id_top = {}
        for page in truth.get("pages", []):
            for f in page.get("figures", []):
                id_top[("figure", f["index"])] = min(f["caption_region"][1], f["body_region"][1])
            for t in page.get("tables", []):
                id_top[("table", t["index"])] = min(t["caption_region"][1], t["body_region"][1])
        tops = [id_top[(it["type"], it["id"])] for it in seq
                if it.get("type") in ("figure", "table") and (it["type"], it.get("id")) in id_top]
        if tops != sorted(tops):
            counts["sequence_order_failures"] += 1
            errs.append(f"{cid}: layout_sequence order does not match actual y order: {tops}")
    return errs, counts


def run_self_check(gallery_dir: Path) -> dict:
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
    if not (30 <= total_cases <= 80):
        errors.append(f"total case count out of 30-80 range: {total_cases}")

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

    # --- D9: generic body text must not overlap target regions (truth contamination) ---
    contamination = 0
    for cid, truth in truths.items():
        if truth.get("intentional_overlap_stress"):
            continue
        for page in truth.get("pages", []):
            targets: list[tuple[str, list]] = []
            for f in page.get("figures", []):
                for r in ("caption_region", "body_region", "context_region"):
                    if f.get(r):
                        targets.append((f"figure {f.get('index')} {r}", f[r]))
            for t in page.get("tables", []):
                for r in ("caption_region", "body_region", "context_region"):
                    if t.get(r):
                        targets.append((f"table {t.get('index')} {r}", t[r]))
            for nt in page.get("non_target_text_regions", []):
                nb = nt["bbox"]
                for label, tb in targets:
                    if _iou(nb, tb) > 0.0:
                        contamination += 1
                        errors.append(
                            f"{cid} p{page['page']}: generic body text {nb} overlaps target {label} {tb} "
                            f"(truth contamination; set intentional_overlap_stress=true only if deliberate)")

    # --- D9 step2/3: layout sequence / title-gap consistency ------------------
    layout_errors, layout_counts = _check_layout_consistency(truths)
    errors.extend(layout_errors)

    # --- D3.5: truth-region vs PDF text-extraction overlap (handoff T2.1) -----
    overlap_errors, overlap_report = check_text_overlap(gallery_dir, case_ids)
    errors.extend(overlap_errors)

    d9_gates = {
        "generic_text_target_overlaps": contamination,
        "target_target_unintended_overlaps": layout_counts["target_target_unintended_overlaps"],
        "sequence_order_failures": layout_counts["sequence_order_failures"],
        "interstitial_line_count_failures": layout_counts["interstitial_line_count_failures"],
        "title_position_failures": layout_counts["title_position_failures"],
        "title_gap_failures": layout_counts["title_gap_failures"],
        "checked": layout_counts["checked"],
    }
    # Persist a durable self-check report so skip reasons / gate results are never silent.
    (gallery_dir / "SELF_CHECK_REPORT.json").write_text(
        json.dumps({"text_overlap": overlap_report, "d9_gates": d9_gates}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if errors:
        raise AssertionError("RTM factory self-check failed:\n" + "\n".join(errors))
    return {"text_overlap": overlap_report, "d9_gates": d9_gates}
