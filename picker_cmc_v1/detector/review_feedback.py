"""D19: real-PDF operator review feedback schema + summary.

A real PDF has no ground truth, so the detector's output is reviewed by a human.
This module defines a small, web-editor-friendly feedback contract
(`real-pdf-review-v0`): the operator marks each detected figure/table with a
decision (accept / a specific issue) and can list objects the detector missed.
``summarize()`` turns that into per-issue counts and a list of recommended next
detector tasks. Nothing here tunes the detector or touches truth/RTM — it only
records and aggregates human judgement.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REVIEW_SCHEMA_VERSION = "real-pdf-review-v0"

# accept = good; everything else is an issue the operator is flagging.
ACCEPT = "accept"
ISSUE_DECISIONS = (
    "false_positive", "missed_object",
    "bad_caption_region", "bad_body_region", "bad_context_region",
    "wrong_title", "wrong_index", "common_region_issue",
)
DECISIONS = (ACCEPT,) + ISSUE_DECISIONS

_OBJECT_ID_RE = re.compile(r"^(figure|table):([^:]+):page(\d+)$")
_REGION_KEYS = ("caption_region", "body_region", "context_region")

# Issue -> the detector improvement task it implies.
_NEXT_TASK = {
    "bad_body_region": "Improve body_region inference for flagged figures/tables (e.g. waveform lower-bound).",
    "bad_caption_region": "Improve caption_region band inference.",
    "bad_context_region": "Improve context_region inference.",
    "wrong_title": "Improve title text extraction.",
    "wrong_index": "Improve index parsing.",
    "false_positive": "Strengthen anchor false-positive guards.",
    "common_region_issue": "Revisit common-region / watermark detection.",
    "missed_object": "Improve anchor recall for missed figures/tables.",
}


class ReviewError(Exception):
    """Raised when a review_result document violates the contract."""


def object_id_for(kind: str, index: str, page: int) -> str:
    return f"{kind}:{index}:page{page}"


def parse_object_id(object_id: Any) -> Tuple[str, str, int]:
    if not isinstance(object_id, str) or not _OBJECT_ID_RE.match(object_id):
        raise ReviewError(f"invalid object_id: {object_id!r} (expected '<figure|table>:<index>:page<N>')")
    m = _OBJECT_ID_RE.match(object_id)
    return m.group(1), m.group(2), int(m.group(3))


def detected_object_ids(detected: Dict[str, Any]) -> set:
    """All object_ids present in a detector-output-v0 manifest."""
    ids = set()
    for case in detected.get("cases", []):
        for page in case.get("pages", []):
            pno = page.get("page")
            for kind in ("figures", "tables"):
                for obj in page.get(kind, []):
                    ids.add(object_id_for(kind[:-1], obj.get("index"), pno))
    return ids


def build_review_template(pages: List[Dict[str, Any]], pdf_name: str, *, reviewer: str = "manual") -> Dict[str, Any]:
    """A pre-filled review skeleton (every detected object -> decision: accept)."""
    objects = []
    for page in pages:
        pno = page.get("page")
        for kind in ("figures", "tables"):
            for obj in page.get(kind, []):
                objects.append({
                    "object_id": object_id_for(kind[:-1], obj.get("index"), pno),
                    "decision": ACCEPT,
                    "notes": "",
                })
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "pdf": pdf_name,
        "reviewer": reviewer,
        "objects": objects,
        "missed_objects": [],
    }


def load_review(path: str | Path) -> Dict[str, Any]:
    """Load a review_result document (YAML or JSON)."""
    path = Path(path)
    if not path.exists():
        raise ReviewError(f"review file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(text)
    elif path.suffix.lower() == ".json":
        data = json.loads(text)
    else:                                    # unknown suffix: try yaml then json
        try:
            import yaml
            data = yaml.safe_load(text)
        except Exception:
            data = json.loads(text)
    if not isinstance(data, dict):
        raise ReviewError("review_result root must be a mapping")
    return data


def _is_bbox(v: Any) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 4
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v))


def validate_review(review: Dict[str, Any], detected: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return a list of contract violations (empty == valid)."""
    errors: List[str] = []
    if review.get("schema_version") != REVIEW_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REVIEW_SCHEMA_VERSION!r} (got {review.get('schema_version')!r})")
    if not isinstance(review.get("pdf"), str) or not review.get("pdf"):
        errors.append("pdf must be a non-empty string")

    known = detected_object_ids(detected) if detected is not None else None

    objects = review.get("objects", [])
    if not isinstance(objects, list):
        errors.append("objects must be a list")
        objects = []
    for i, obj in enumerate(objects):
        op = f"objects[{i}]"
        if not isinstance(obj, dict):
            errors.append(f"{op} must be a mapping")
            continue
        try:
            parse_object_id(obj.get("object_id"))
        except ReviewError as exc:
            errors.append(f"{op}: {exc}")
        if obj.get("decision") not in DECISIONS:
            errors.append(f"{op}: unknown decision {obj.get('decision')!r} (allowed: {DECISIONS})")
        if known is not None and isinstance(obj.get("object_id"), str) and obj["object_id"] not in known:
            errors.append(f"{op}: object_id {obj['object_id']!r} not found in detected manifest")
        ec = obj.get("expected_change")
        if ec is not None:
            if not isinstance(ec, dict):
                errors.append(f"{op}.expected_change must be a mapping")
            else:
                for k, v in ec.items():
                    if k not in _REGION_KEYS:
                        errors.append(f"{op}.expected_change has unknown region {k!r}")
                    elif not _is_bbox(v):
                        errors.append(f"{op}.expected_change.{k} must be 4 numbers")

    missed = review.get("missed_objects", [])
    if not isinstance(missed, list):
        errors.append("missed_objects must be a list")
        missed = []
    for i, mo in enumerate(missed):
        mp = f"missed_objects[{i}]"
        if not isinstance(mo, dict):
            errors.append(f"{mp} must be a mapping")
            continue
        if mo.get("kind") not in ("figure", "table"):
            errors.append(f"{mp}.kind must be 'figure' or 'table'")
        if not isinstance(mo.get("page"), int):
            errors.append(f"{mp}.page must be an integer")
        if "approximate_region" in mo and mo["approximate_region"] is not None and not _is_bbox(mo["approximate_region"]):
            errors.append(f"{mp}.approximate_region must be 4 numbers when present")
    return errors


def validate_or_raise(review: Dict[str, Any], detected: Optional[Dict[str, Any]] = None) -> None:
    errors = validate_review(review, detected)
    if errors:
        raise ReviewError("real-pdf-review-v0 invalid:\n" + "\n".join(errors))


def summarize(review: Dict[str, Any], detected: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Aggregate operator decisions into counts + recommended next detector tasks."""
    validate_or_raise(review, detected)
    objects = review.get("objects", [])
    missed = review.get("missed_objects", [])

    decisions = Counter(o.get("decision") for o in objects)
    issues: Dict[str, int] = {k: 0 for k in ISSUE_DECISIONS}
    for d, n in decisions.items():
        if d in issues:
            issues[d] += n
    issues["missed_object"] += len(missed)        # missed_objects list folds into the missed_object issue

    next_tasks: List[str] = []
    for issue, task in _NEXT_TASK.items():
        if issues.get(issue, 0) > 0 and task not in next_tasks:
            next_tasks.append(task)

    return {
        "ok": True,
        "schema_version": REVIEW_SCHEMA_VERSION,
        "pdf": review.get("pdf"),
        "reviewer": review.get("reviewer", "manual"),
        "reviewed_objects": len(objects),
        "accepted": decisions.get(ACCEPT, 0),
        "missed_objects": len(missed),
        "issues": issues,
        "recommended_next_tasks": next_tasks,
    }
