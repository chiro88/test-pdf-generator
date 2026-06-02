"""Detector-vs-truth golden comparison harness (handoff T4 / D4).

Compares a detector output manifest against RTM truth JSON with per-region,
per-axis tolerance and identity-key matching, and emits a JSON + markdown diff
report. This module is NOT a detector; it only judges a detector's output.

    comparison pass != detector correctness on real documents
    (it only proves the detector matches the frozen truth within tolerance)

Design is intentionally modular (no giant compare() with nested if/else):
  ToleranceProfile / ComparisonConfig  — knobs
  MatchKey / extract_objects()         — identity-key extraction
  compare_bbox / compare_object()      — leaf comparisons
  compare_cases()                      — orchestration
  load_truth_cases / load_detected_manifest / write_compare_report  — I/O
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class InvalidInput(Exception):
    """Raised for malformed truth/detected input (CLI maps this to exit code 2)."""


# --- tolerance ---------------------------------------------------------------
# (x_pt, y_pt) per region type. y-band detection cares about y far more than x.
STRICT_TOLERANCE: Dict[str, Tuple[float, float]] = {
    "header": (8.0, 5.0),
    "footer": (8.0, 5.0),
    "watermark": (14.0, 14.0),
    "caption_region": (8.0, 5.0),
    "body_region": (12.0, 8.0),
    "context_region": (14.0, 10.0),
}
# A development convenience profile; default stays strict.
LOOSE_TOLERANCE: Dict[str, Tuple[float, float]] = {k: (x * 2, y * 2) for k, (x, y) in STRICT_TOLERANCE.items()}

TOLERANCE_PROFILES = {"strict": STRICT_TOLERANCE, "loose": LOOSE_TOLERANCE}

# Exact-match (non-bbox) table identity/state fields.
TABLE_FIELDS = ["table_group_id", "part_index", "is_continuation", "continuation_marker", "continued_from"]


@dataclass
class ToleranceProfile:
    name: str
    table: Dict[str, Tuple[float, float]]

    @classmethod
    def named(cls, name: str) -> "ToleranceProfile":
        if name not in TOLERANCE_PROFILES:
            raise InvalidInput(f"unknown tolerance profile: {name}")
        return cls(name=name, table=TOLERANCE_PROFILES[name])

    def for_region(self, region_name: str, kind: Optional[str] = None) -> Tuple[float, float]:
        key = kind if region_name == "bbox" else region_name
        if key not in self.table:
            raise InvalidInput(f"no tolerance defined for region '{region_name}' kind '{kind}'")
        return self.table[key]


@dataclass
class ComparisonConfig:
    tolerance: ToleranceProfile = field(default_factory=lambda: ToleranceProfile.named("strict"))
    allow_extra: bool = False
    case_id_filter: Optional[str] = None
    region_kind_filter: Optional[str] = None  # 'figure' | 'table' | 'header' | 'footer' | 'watermark'


# --- identity-key object extraction ------------------------------------------
MatchKey = Tuple

def _norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def extract_objects(case: Dict[str, Any]) -> Dict[MatchKey, Dict[str, Any]]:
    """Flatten one case's pages into {identity_key: object_descriptor}.

    Each descriptor: {kind, page, regions:{name:bbox}, fields:{name:value}, index}.
    Identity keys (NOT bbox-based, so missing/extra objects are caught):
      common region: (common, page, kind, ordinal-within-(page,kind))
      figure:        (figure, page, index)
      table:         (table, group_id, part_index)  [fallback (table, page, index, part_index)]
    """
    out: Dict[MatchKey, Dict[str, Any]] = {}
    for page in case.get("pages", []):
        pg = page.get("page")
        ordinals: Dict[str, int] = {}
        for reg in page.get("common_regions", []):
            kind = reg.get("kind")
            ordn = ordinals.get(kind, 0)
            ordinals[kind] = ordn + 1
            key = ("common", pg, kind, ordn)
            out[key] = {
                "kind": kind, "page": pg, "index": "",
                "regions": {"bbox": reg.get("bbox")},
                "fields": {},
            }
        for fig in page.get("figures", []):
            idx = fig.get("index")
            key = ("figure", pg, idx)
            out[key] = {
                "kind": "figure", "page": pg, "index": idx,
                "regions": {r: fig.get(r) for r in ("caption_region", "body_region", "context_region") if fig.get(r) is not None},
                "fields": {},
            }
        for tbl in page.get("tables", []):
            idx = tbl.get("index")
            gid = tbl.get("table_group_id")
            part = tbl.get("part_index")
            key = ("table", gid, part) if gid is not None else ("table", pg, idx, part)
            regions = {r: tbl.get(r) for r in ("caption_region", "body_region", "context_region") if tbl.get(r) is not None}
            fields = {f: tbl.get(f) for f in TABLE_FIELDS if f in tbl}
            out[key] = {"kind": "table", "page": pg, "index": idx, "regions": regions, "fields": fields}
    return out


def _kind_passes_filter(kind: str, config: ComparisonConfig) -> bool:
    return config.region_kind_filter is None or config.region_kind_filter == kind


# --- leaf comparisons --------------------------------------------------------
def compare_bbox(region_name: str, kind: str, expected: Optional[list], actual: Optional[list],
                 tol: ToleranceProfile) -> Dict[str, Any]:
    tx, ty = tol.for_region(region_name, kind)
    if expected is None or actual is None:
        return {"region": region_name, "expected": expected, "actual": actual,
                "delta": None, "tolerance": {"x": tx, "y": ty}, "passed": False,
                "reason": "missing region in " + ("detected" if actual is None else "truth")}
    delta = [round(actual[i] - expected[i], 2) for i in range(4)]
    passed = abs(delta[0]) <= tx and abs(delta[2]) <= tx and abs(delta[1]) <= ty and abs(delta[3]) <= ty
    return {"region": region_name, "expected": expected, "actual": actual,
            "delta": delta, "tolerance": {"x": tx, "y": ty}, "passed": passed}


def compare_object(key: MatchKey, truth_obj: Optional[Dict], det_obj: Optional[Dict],
                   config: ComparisonConfig) -> Dict[str, Any]:
    """Compare one matched/missing/extra object; returns an object comparison record."""
    base = {"key": list(key), "regions": [], "fields": []}
    if truth_obj is not None:
        base.update(kind=truth_obj["kind"], page=truth_obj["page"], index=truth_obj["index"])
    else:
        base.update(kind=det_obj["kind"], page=det_obj["page"], index=det_obj["index"])

    if det_obj is None:
        base["status"] = "missing"
        base["passed"] = False
        return base
    if truth_obj is None:
        base["status"] = "extra"
        base["passed"] = config.allow_extra
        return base

    base["status"] = "matched"
    kind = truth_obj["kind"]
    region_kind = kind if kind in ("header", "footer", "watermark") else None
    for region_name, exp_bbox in truth_obj["regions"].items():
        base["regions"].append(
            compare_bbox(region_name, region_kind, exp_bbox, det_obj["regions"].get(region_name), config.tolerance)
        )
    for fname, exp_val in truth_obj["fields"].items():
        act_val = det_obj["fields"].get(fname, "<<missing>>")
        base["fields"].append({"field": fname, "expected": exp_val, "actual": act_val, "passed": act_val == exp_val})

    base["passed"] = all(r["passed"] for r in base["regions"]) and all(f["passed"] for f in base["fields"])
    return base


# --- I/O ---------------------------------------------------------------------
def _require_coords(obj: Dict[str, Any], where: str) -> None:
    if obj.get("coordinate_unit") != "pdf_pt":
        raise InvalidInput(f"{where}: coordinate_unit must be 'pdf_pt' (got {obj.get('coordinate_unit')!r})")
    if obj.get("coordinate_origin") != "top-left":
        raise InvalidInput(f"{where}: coordinate_origin must be 'top-left' (got {obj.get('coordinate_origin')!r})")


def load_truth_cases(truth_root: Path | str, case_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    truth_root = Path(truth_root)
    manifest_path = truth_root / "MANIFEST.json"
    if not manifest_path.exists():
        raise InvalidInput(f"truth-root has no MANIFEST.json: {truth_root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: Dict[str, Dict[str, Any]] = {}
    for entry in manifest.get("cases", []):
        cid = entry["case_id"]
        if case_filter and cid != case_filter:
            continue
        truth_path = truth_root / cid / f"{cid}.truth.json"
        if not truth_path.exists():
            raise InvalidInput(f"missing truth.json for case {cid}: {truth_path}")
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        _require_coords(truth, f"truth {cid}")
        cases[cid] = truth
    if not cases:
        raise InvalidInput("no truth cases selected")
    return cases


def load_detected_manifest(path: Path | str) -> Dict[str, Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise InvalidInput(f"detected manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("schema_version"):
        raise InvalidInput("detected manifest missing schema_version")
    _require_coords(data, "detected manifest")
    return {c["case_id"]: c for c in data.get("cases", [])}


# --- orchestration -----------------------------------------------------------
def compare_cases(truth_cases: Dict[str, Dict], detected: Dict[str, Dict], config: ComparisonConfig) -> Dict[str, Any]:
    case_reports: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    summary = {"cases_total": 0, "cases_passed": 0, "cases_failed": 0,
               "objects_expected": 0, "objects_matched": 0, "objects_missing": 0, "objects_extra": 0,
               "regions_checked": 0, "regions_failed": 0}

    all_case_ids = list(truth_cases.keys()) + [c for c in detected if c not in truth_cases]
    for cid in all_case_ids:
        truth_objs = extract_objects(truth_cases[cid]) if cid in truth_cases else {}
        det_objs = extract_objects(detected[cid]) if cid in detected else {}
        # apply region-kind filter
        if config.region_kind_filter:
            truth_objs = {k: v for k, v in truth_objs.items() if _kind_passes_filter(v["kind"], config)}
            det_objs = {k: v for k, v in det_objs.items() if _kind_passes_filter(v["kind"], config)}

        objects: List[Dict[str, Any]] = []
        for key in list(truth_objs.keys()):
            objects.append(compare_object(key, truth_objs[key], det_objs.get(key), config))
        for key in det_objs:
            if key not in truth_objs:
                objects.append(compare_object(key, None, det_objs[key], config))

        case_passed = True
        for obj in objects:
            summary["objects_expected"] += 1 if obj["status"] != "extra" else 0
            if obj["status"] == "matched":
                summary["objects_matched"] += 1
            elif obj["status"] == "missing":
                summary["objects_missing"] += 1
            elif obj["status"] == "extra":
                summary["objects_extra"] += 1
            summary["regions_checked"] += len(obj["regions"])
            summary["regions_failed"] += sum(1 for r in obj["regions"] if not r["passed"])
            if not obj["passed"]:
                case_passed = False
                failures.append({"case_id": cid, **obj})

        summary["cases_total"] += 1
        if case_passed:
            summary["cases_passed"] += 1
        else:
            summary["cases_failed"] += 1
        case_reports.append({"case_id": cid, "passed": case_passed, "objects": objects})

    return {"summary": summary, "failures": failures, "cases": case_reports,
            "config": {"tolerance_profile": config.tolerance.name, "allow_extra": config.allow_extra,
                       "case_id_filter": config.case_id_filter, "region_kind_filter": config.region_kind_filter}}


def _md_report(report: Dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# RTM detector-vs-truth comparison report",
        "",
        f"- tolerance profile: `{report['config']['tolerance_profile']}`  ·  allow_extra: {report['config']['allow_extra']}",
        f"- cases: {s['cases_passed']}/{s['cases_total']} passed ({s['cases_failed']} failed)",
        f"- objects: expected {s['objects_expected']}, matched {s['objects_matched']}, missing {s['objects_missing']}, extra {s['objects_extra']}",
        f"- regions: {s['regions_checked'] - s['regions_failed']}/{s['regions_checked']} within tolerance ({s['regions_failed']} failed)",
        "",
    ]
    if report["failures"]:
        lines.append("## Failures")
        lines.append("")
        lines.append("| case_id | kind | index | status | detail |")
        lines.append("|---|---|---|---|---|")
        for f in report["failures"]:
            if f["status"] in ("missing", "extra"):
                detail = f["status"]
            else:
                bad_r = [f"{r['region']} Δ{r['delta']} tol{(r['tolerance']['x'], r['tolerance']['y'])}" for r in f["regions"] if not r["passed"]]
                bad_f = [f"{x['field']}: exp {x['expected']!r} got {x['actual']!r}" for x in f["fields"] if not x["passed"]]
                detail = "; ".join(bad_r + bad_f)
            lines.append(f"| `{f['case_id']}` | {f['kind']} | {f['index']} | {f['status']} | {detail} |")
    else:
        lines.append("All comparisons passed within tolerance.")
    return "\n".join(lines) + "\n"


def write_compare_report(report: Dict[str, Any], out_dir: Path | str) -> Tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "compare_report.json"
    md_path = out_dir / "compare_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_md_report(report), encoding="utf-8")
    return json_path, md_path
