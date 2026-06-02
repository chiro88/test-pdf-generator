"""Unified RTM CLI (D5.5): one entrypoint, machine-readable --json, stable exit codes.

Every command wraps existing RTM functionality (generation, self-check,
promotion, compare, overlay) and, with --json, prints exactly one JSON object
to stdout. Warnings go to stderr so JSON parsing never breaks. Errors are
RtmError with a stable error_code (see errors.py) and exit code.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .compare import (
    ComparisonConfig,
    InvalidInput,
    ToleranceProfile,
    compare_cases,
    load_detected_manifest,
    load_truth_cases,
    write_compare_report,
)
from .coverage import coverage_summary, derive_tags
from .errors import RtmError
from .gallery import write_index, write_manifest
from .overlay import OverlayConfig
from .overlay import generate as overlay_generate
from .promote import PromotionError, promote
from .render import build_pdf
from .scenario_io import list_scenarios, list_templates, load_scenario_file, scenario_to_casespec
from .scenario_specs import all_cases
from .self_check import run_self_check

DEFAULT_GALLERY = Path("rtm_gallery")


# --- shared building blocks --------------------------------------------------
def generate_gallery(out_dir: Path | str, seed: int = 1234, force: bool = False) -> Dict[str, Any]:
    out = Path(out_dir)
    if out.exists():
        if not force:
            raise RtmError("OUTPUT_DIR_EXISTS", f"output dir already exists: {out} (use --force)", field="out")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    cases = all_cases()
    entries: List[Dict[str, Any]] = []
    try:
        for case in cases:
            truth, png_paths = build_pdf(case, out / case.case_id)
            entries.append({
                "case_id": case.case_id, "axes": case.axes, "realistic": case.realistic,
                "pdf": f"{case.case_id}/{case.case_id}.pdf",
                "truth": f"{case.case_id}/{case.case_id}.truth.json",
                "preview": f"{case.case_id}/{png_paths[0].name}",
                "page_count": len(truth["pages"]), "coverage_tags": derive_tags(case),
            })
        write_manifest(out, entries, coverage_summary(cases))
        write_index(out, cases)
    except Exception as exc:  # noqa: BLE001 - surface as a clean error
        raise RtmError("PDF_GENERATION_FAILED", f"gallery generation failed: {exc}")
    try:
        report = run_self_check(out)
    except AssertionError as exc:
        raise RtmError("SELF_CHECK_FAILED", str(exc))
    ov = report["text_overlap"]
    return {
        "gallery": str(out), "case_count": len(cases),
        "manifest": str(out / "MANIFEST.json"), "index": str(out / "index.md"),
        "self_check_report": str(out / "SELF_CHECK_REPORT.json"),
        "text_overlap": {"checked": ov["checked"], "passed": ov["passed"], "skipped": len(ov["skipped"])},
    }


def _render_single_case(case, out_dir: Path) -> Dict[str, Any]:
    case_dir = out_dir / case.case_id
    try:
        truth, png_paths = build_pdf(case, case_dir)
    except Exception as exc:  # noqa: BLE001
        raise RtmError("PDF_GENERATION_FAILED", f"failed to render case {case.case_id}: {exc}")
    return {
        "case_id": case.case_id, "output_dir": str(out_dir),
        "pdf": str(case_dir / f"{case.case_id}.pdf"),
        "truth": str(case_dir / f"{case.case_id}.truth.json"),
        "previews": [str(p) for p in png_paths],
        "notes": str(case_dir / f"{case.case_id}.notes.md"),
        "page_count": len(truth["pages"]),
    }


# --- command handlers (each returns a payload dict, may raise RtmError) -------
def cmd_generate(args) -> Dict[str, Any]:
    return {"ok": True, "command": "generate", **generate_gallery(args.out, args.seed, args.force)}


def cmd_generate_case(args) -> Dict[str, Any]:
    if args.scenario_file:
        case = scenario_to_casespec(load_scenario_file(args.scenario_file))
    else:
        if not args.case_id:
            raise RtmError("INVALID_INPUT", "generate-case needs --case-id or --scenario-file", field="case_id")
        by_id = {c.case_id: c for c in all_cases()}
        if args.case_id not in by_id:
            raise RtmError("INVALID_INPUT", f"unknown built-in scenario: {args.case_id}",
                           field="case_id", allowed_values=sorted(by_id))
        case = by_id[args.case_id]
    out = Path(args.out)
    if (out / case.case_id).exists() and not args.force:
        raise RtmError("OUTPUT_DIR_EXISTS", f"case output already exists: {out / case.case_id} (use --force)", field="out")
    if (out / case.case_id).exists():
        shutil.rmtree(out / case.case_id)
    out.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "command": "generate-case", **_render_single_case(case, out)}


def cmd_list_scenarios(args) -> Dict[str, Any]:
    return {"ok": True, "command": "list-scenarios", "scenarios": list_scenarios()}


def cmd_list_templates(args) -> Dict[str, Any]:
    return {"ok": True, "command": "list-templates", "templates": list_templates()}


def cmd_validate_scenario(args) -> Dict[str, Any]:
    case = scenario_to_casespec(load_scenario_file(args.scenario_file))
    return {"ok": True, "command": "validate-scenario", "valid": True, "case_id": case.case_id,
            "figures": len(case.figures), "tables": len(case.tables), "page_count": case.page.page_count}


def cmd_self_check(args) -> Dict[str, Any]:
    gallery = Path(args.gallery)
    if not (gallery / "MANIFEST.json").exists():
        raise RtmError("INVALID_INPUT", f"gallery MANIFEST.json not found: {gallery} (run generate first)", field="gallery")
    try:
        report = run_self_check(gallery)
    except AssertionError as exc:
        raise RtmError("SELF_CHECK_FAILED", str(exc))
    manifest = json.loads((gallery / "MANIFEST.json").read_text(encoding="utf-8"))
    cov = manifest.get("coverage_summary", {})
    ov = report["text_overlap"]
    return {"ok": True, "command": "self-check", "passed": True, "gallery": str(gallery),
            "coverage": {"total_cases": cov.get("total_cases"), "missing": cov.get("missing", []),
                         "below_min": cov.get("below_min", [])},
            "text_overlap": {"checked": ov["checked"], "passed": ov["passed"],
                             "skipped": len(ov["skipped"]), "failures": len(ov["failures"])}}


def cmd_promote(args) -> Dict[str, Any]:
    keep = [s.strip() for s in args.keep.split(",") if s.strip()] if args.keep else None
    try:
        result = promote(args.gallery, args.out, keep_override=keep, force=args.force, allow_empty=args.allow_empty)
    except PromotionError as exc:
        raise RtmError("PROMOTION_FAILED", str(exc))
    return {"ok": True, "command": "promote", "selected": result["selected"], "dropped": result["dropped"],
            "selection_source": result["selection_source"], "out_dir": result["out_dir"]}


def cmd_compare(args) -> Dict[str, Any]:
    try:
        config = ComparisonConfig(tolerance=ToleranceProfile.named(args.tolerance_profile), allow_extra=args.allow_extra)
        truth_cases = load_truth_cases(args.truth_root)
        detected = load_detected_manifest(args.detected)
        report = compare_cases(truth_cases, detected, config)
    except InvalidInput as exc:
        raise RtmError("INVALID_INPUT", str(exc))
    json_path, md_path = write_compare_report(report, args.out)
    passed = report["summary"]["cases_failed"] == 0
    return {"ok": True, "command": "compare", "passed": passed, "summary": report["summary"],
            "report_json": str(json_path), "report_md": str(md_path)}


def cmd_overlay(args) -> Dict[str, Any]:
    try:
        pages = [int(x) for x in args.pages.split(",") if x.strip()] if args.pages else None
    except ValueError:
        raise RtmError("INVALID_INPUT", f"--pages must be comma-separated integers (got {args.pages!r})", field="pages")
    config = OverlayConfig(scale=args.scale, failures_only=args.failures_only, all_cases=args.all_cases,
                           case_id_filter=args.case_id, pages_filter=pages)
    try:
        result = overlay_generate(args.truth_root, args.detected, args.compare_report, args.out, config)
    except InvalidInput as exc:
        raise RtmError("INVALID_INPUT", str(exc))
    except Exception as exc:  # noqa: BLE001
        raise RtmError("OVERLAY_FAILED", f"overlay rendering failed: {exc}")
    return {"ok": True, "command": "overlay", "pages_rendered": result["pages_rendered"],
            "cases": len(result["cases"]), "manifest": result["manifest"], "index": result["index"]}


# --- argument parser ---------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rtm_cli", description="RTM PDF factory CLI (LLM/agent friendly).")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit a single machine-readable JSON object to stdout")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_):
        return sub.add_parser(name, help=help_, parents=[common])

    g = add("generate", "generate the full RTM gallery")
    g.add_argument("--out", default=str(DEFAULT_GALLERY)); g.add_argument("--seed", type=int, default=1234)
    g.add_argument("--force", action="store_true"); g.set_defaults(func=cmd_generate)

    gc = add("generate-case", "generate one named or scenario-file case")
    gc.add_argument("--case-id", default=None); gc.add_argument("--scenario-file", default=None)
    gc.add_argument("--out", default="artifacts/rtm_case"); gc.add_argument("--force", action="store_true")
    gc.set_defaults(func=cmd_generate_case)

    add("list-scenarios", "list built-in scenario ids").set_defaults(func=cmd_list_scenarios)
    add("list-templates", "list header/footer/watermark/figure/table templates").set_defaults(func=cmd_list_templates)

    vs = add("validate-scenario", "validate a scenario file")
    vs.add_argument("scenario_file"); vs.set_defaults(func=cmd_validate_scenario)

    sc = add("self-check", "run self-check (coverage + text overlap)")
    sc.add_argument("--gallery", default=str(DEFAULT_GALLERY)); sc.set_defaults(func=cmd_self_check)

    pr = add("promote", "promote kept gallery cases to frozen")
    pr.add_argument("--gallery", default=str(DEFAULT_GALLERY)); pr.add_argument("--out", default="rtm_frozen")
    pr.add_argument("--keep", default=None); pr.add_argument("--force", action="store_true")
    pr.add_argument("--allow-empty", action="store_true"); pr.set_defaults(func=cmd_promote)

    cp = add("compare", "compare detector output vs truth")
    cp.add_argument("--truth-root", required=True); cp.add_argument("--detected", required=True)
    cp.add_argument("--out", default="artifacts/rtm_compare")
    cp.add_argument("--tolerance-profile", default="strict", choices=["strict", "loose"])
    cp.add_argument("--allow-extra", action="store_true"); cp.set_defaults(func=cmd_compare)

    ov = add("overlay", "render overlay artifacts from a compare report")
    ov.add_argument("--truth-root", required=True); ov.add_argument("--detected", required=True)
    ov.add_argument("--compare-report", required=True); ov.add_argument("--out", default="artifacts/rtm_overlay")
    ov.add_argument("--case-id", default=None); ov.add_argument("--failures-only", action="store_true")
    ov.add_argument("--all", dest="all_cases", action="store_true"); ov.add_argument("--pages", default=None)
    ov.add_argument("--scale", type=float, default=1.5); ov.set_defaults(func=cmd_overlay)
    return p


def _emit(payload: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        cmd = payload.get("command")
        extra = {k: v for k, v in payload.items() if k not in ("ok", "command")}
        print(f"{cmd}: ok" + (f" — {json.dumps(extra, ensure_ascii=False)}" if extra else ""))


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    as_json = args.json
    try:
        payload = args.func(args)
    except RtmError as exc:
        if as_json:
            print(json.dumps(exc.to_json(), ensure_ascii=False))
        else:
            print(f"error [{exc.error_code}]: {exc.message}", file=sys.stderr)
        return exc.exit_code
    exit_code = 1 if payload.get("passed") is False else 0
    _emit(payload, as_json)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
