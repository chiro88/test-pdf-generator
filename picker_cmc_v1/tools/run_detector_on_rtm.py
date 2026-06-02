#!/usr/bin/env python3
"""Run a detector over the RTM frozen fixtures and wire it to compare/overlay (D10).

    python tools/run_detector_on_rtm.py \
        --rtm-root picker_cmc_v1/tests/fixtures/rtm_frozen \
        --out artifacts/detector_rtm --json

    # real detector (per-case): the cmd must write a JSON {"pages":[...]} to {out}
    python tools/run_detector_on_rtm.py --rtm-root <frozen> --out <dir> \
        --detector-cmd "python -m picker_cmc.detector --pdf {pdf} --out {out}" --json

This is the *integration path*, not a detector. A `--synthetic-from-truth`
adapter exists ONLY as a contract test (it copies truth → producer.mode is
labelled 'synthetic-contract-test' and it makes no correctness claim).

Exit: 0 compare passed · 1 compare failed (detector mismatch) · 2 invalid input /
detector unavailable / contract-invalid output · 3 internal error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_THIS = Path(__file__).resolve()
ROOT = _THIS.parents[2]                                   # real_tracking_mock_v1
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))           # detector_output package
sys.path.insert(0, str(ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"))  # rtm_factory

from detector_output import writer                         # noqa: E402
from detector_output.validator import DetectorOutputError, validate_or_raise  # noqa: E402
from rtm_factory.compare import (  # noqa: E402
    ComparisonConfig, InvalidInput, ToleranceProfile,
    compare_cases, load_detected_manifest, load_truth_cases, write_compare_report,
)
from rtm_factory.overlay import OverlayConfig  # noqa: E402
from rtm_factory.overlay import generate as overlay_generate  # noqa: E402


class RunnerError(Exception):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.message = message
        self.code = code


def _load_frozen(rtm_root: Path):
    man_path = rtm_root / "MANIFEST.json"
    if not man_path.exists():
        raise RunnerError(f"rtm-root has no MANIFEST.json: {rtm_root}")
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not cases:
        raise RunnerError(f"rtm-root MANIFEST has no cases: {rtm_root}")
    return cases


def _truth_pages_to_detected(truth: dict) -> list:
    """Copy truth regions into detector-output pages (contract-test adapter only)."""
    pages = []
    for p in truth.get("pages", []):
        common = [writer.common_region(r["kind"], r["bbox"], r.get("text")) for r in p.get("common_regions", [])]
        figs = [writer.figure(f["index"], f.get("title", ""), f["caption_region"], f["body_region"],
                              f["context_region"], title_position=f.get("title_position", "below"),
                              title_body_gap_lines=f.get("title_body_gap_lines", 0))
                for f in p.get("figures", [])]
        tbls = [writer.table(t["index"], t.get("title", ""), t["table_group_id"], t["caption_region"],
                             t["body_region"], t.get("context_region"), part_index=t.get("part_index", 1),
                             is_continuation=t.get("is_continuation", False),
                             continuation_marker=t.get("continuation_marker"),
                             continued_from=t.get("continued_from"))
                for t in p.get("tables", [])]
        pages.append(writer.page(p["page"], common_regions=common, figures=figs, tables=tbls))
    return pages


def _run_detector_cmd(cmd_tmpl: str, pdf: Path, truth: Path) -> list:
    """Run a real detector cmd that writes {out} = {"pages":[...]} for one case."""
    with tempfile.TemporaryDirectory() as td:
        out_json = Path(td) / "case.json"
        cmd = cmd_tmpl.format(pdf=str(pdf), truth=str(truth), out=str(out_json))
        proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RunnerError(f"detector-cmd failed (rc={proc.returncode}) for {pdf.name}: {proc.stderr[:200]}", code=2)
        if not out_json.exists():
            raise RunnerError(f"detector-cmd produced no output for {pdf.name}", code=2)
        data = json.loads(out_json.read_text(encoding="utf-8"))
        return data.get("pages", [])


def build_detected_manifest(rtm_root: Path, frozen_cases: list, *, detector_cmd: str | None,
                            synthetic: bool) -> dict:
    if not detector_cmd and not synthetic:
        raise RunnerError("detector unavailable: pass --detector-cmd <cmd> or --synthetic-from-truth "
                          "(synthetic is a CONTRACT TEST, not a correctness proof)", code=2)
    out_cases = []
    for entry in frozen_cases:
        cid = entry["case_id"]
        pdf_rel = entry.get("pdf", f"{cid}/{cid}.pdf")
        pdf = rtm_root / pdf_rel
        truth_path = rtm_root / cid / f"{cid}.truth.json"
        if synthetic:
            truth = json.loads(truth_path.read_text(encoding="utf-8"))
            pages = _truth_pages_to_detected(truth)
        else:
            pages = _run_detector_cmd(detector_cmd, pdf, truth_path)
        out_cases.append(writer.case(cid, pdf_rel, pages))
    mode = "synthetic-contract-test" if synthetic else "detector"
    return writer.build_manifest(out_cases, mode=mode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run a detector over RTM frozen fixtures (integration path).")
    ap.add_argument("--rtm-root", default=str(ROOT / "picker_cmc_v1/tests/fixtures/rtm_frozen"))
    ap.add_argument("--out", default="artifacts/detector_rtm")
    ap.add_argument("--detector-cmd", default=None)
    ap.add_argument("--synthetic-from-truth", action="store_true",
                    help="CONTRACT TEST ONLY: copy truth as detector output (no correctness claim)")
    ap.add_argument("--tolerance-profile", default="strict", choices=["strict", "loose"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    def emit(payload, code):
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        elif not payload.get("ok"):
            print(f"error: {payload.get('error')}", file=sys.stderr)
        else:
            print(f"detector-rtm: {payload.get('case_count')} cases, compare passed={payload.get('compare_passed')}")
        return code

    rtm_root = Path(args.rtm_root)
    out = Path(args.out)
    try:
        frozen_cases = _load_frozen(rtm_root)
        manifest = build_detected_manifest(rtm_root, frozen_cases,
                                           detector_cmd=args.detector_cmd, synthetic=args.synthetic_from_truth)
        validate_or_raise(manifest)
        detected_path = writer.write_manifest(out / "detected_manifest.json", manifest)
    except RunnerError as exc:
        return emit({"ok": False, "error_code": "DETECTOR_UNAVAILABLE_OR_INVALID", "error": exc.message}, exc.code)
    except DetectorOutputError as exc:
        return emit({"ok": False, "error_code": "CONTRACT_INVALID", "error": str(exc)}, 2)

    # --- compare ---
    try:
        config = ComparisonConfig(tolerance=ToleranceProfile.named(args.tolerance_profile))
        truth_cases = load_truth_cases(rtm_root)
        detected = load_detected_manifest(detected_path)
        report = compare_cases(truth_cases, detected, config)
    except InvalidInput as exc:
        return emit({"ok": False, "error_code": "COMPARE_INPUT_INVALID", "error": str(exc)}, 2)
    cmp_json, cmp_md = write_compare_report(report, out / "compare")
    passed = report["summary"]["cases_failed"] == 0

    # --- overlay on failures ---
    overlay_info = None
    if not passed:
        try:
            ov = overlay_generate(rtm_root, detected_path, cmp_json, out / "overlay", OverlayConfig(failures_only=True))
            overlay_info = {"manifest": ov["manifest"], "index": ov["index"], "pages_rendered": ov["pages_rendered"]}
        except Exception as exc:  # noqa: BLE001
            return emit({"ok": False, "error_code": "OVERLAY_FAILED", "error": str(exc)}, 3)

    payload = {
        "ok": True, "producer_mode": manifest["producer"]["mode"],
        "case_count": len(frozen_cases), "detected_manifest": str(detected_path),
        "compare_report_json": str(cmp_json), "compare_report_md": str(cmp_md),
        "compare_passed": passed, "summary": report["summary"], "overlay": overlay_info,
        "note": "integration path result; compare_passed reflects fixture match within tolerance, "
                "NOT detector correctness on real documents",
    }
    return emit(payload, 0 if passed else 1)


if __name__ == "__main__":
    sys.exit(main())
