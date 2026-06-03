#!/usr/bin/env python3
"""D28: end-to-end product smoke — exercise the whole flow once and validate.

    python tools/run_product_e2e_smoke.py --pdf /path/to/input.pdf --workdir /tmp/e2e --json

Flow: setup YAML -> detector run -> editor-save-manifest -> one bbox edit -> save ->
reopen -> edited review export -> downstream package export -> validate everything.
No detector tuning, no new features — a release-candidate verification.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # picker_cmc_v1

import yaml  # noqa: E402

from downstream_package.exporter import build_package  # noqa: E402
from downstream_package.validator import validate_package  # noqa: E402
from editor_manifest.validator import validate_manifest as validate_editor  # noqa: E402
from setup.loader import load_setup  # noqa: E402
from setup.template import render_template  # noqa: E402
from setup.validator import validate_setup  # noqa: E402
from web_editor.editing import edit_bbox, save  # noqa: E402
from web_editor.export import export_artifacts  # noqa: E402
from web_editor.models import load_run  # noqa: E402
from web_editor.workflow import run_from_setup  # noqa: E402


def _first_object(manifest):
    for p in manifest.get("pages", []):
        for kind in ("figures", "tables"):
            if p.get(kind):
                return kind[:-1], p[kind][0], p["page"]
    return None


def run_e2e(pdf: str | Path, workdir: str | Path) -> dict:
    """Run the full product flow once; return a per-stage summary. Raises on failure."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    run_dir = workdir / "run"
    stages: dict = {}

    # 1. setup YAML (from the template, filled)
    cfg = yaml.safe_load(render_template())
    cfg["project"]["name"] = "e2e"
    cfg["input"]["pdf_path"] = str(pdf)
    cfg["output"]["artifact_dir"] = str(run_dir)
    cfg["output"]["save_manifest_path"] = str(run_dir / "editor_save_manifest.json")
    setup_path = workdir / "setup.yaml"
    setup_path.write_text(yaml.safe_dump(cfg))
    validate_setup(load_setup(setup_path))
    stages["setup_valid"] = True

    # 2. run the detector from the setup
    rd = run_from_setup(load_setup(setup_path))
    stages["detector_run"] = (rd / "detected_manifest.json").exists()

    # 3. open + validate the editor-save-manifest
    ctx = load_run(rd)
    assert validate_editor(ctx.manifest) == [], "editor manifest invalid"
    stages["editor_manifest_valid"] = True

    # 4. apply one bbox edit through the edit path
    found = _first_object(ctx.manifest)
    assert found is not None, "no figure/table to edit"
    kind, obj, page = found
    oid = f"{kind}:{obj['index']}:page{page}"
    before = list(obj["body_region"])
    after = [round(before[0] - 2, 2), round(before[1] - 2, 2), round(before[2] + 2, 2), round(before[3] + 2, 2)]
    edit_bbox(ctx, oid, "body_region", after)
    save(ctx)
    stages["edit_saved"] = True

    # 5. reopen — the edit persists
    ctx2 = load_run(rd)
    live = _first_object(ctx2.manifest)[1]
    stages["edit_persists"] = live["body_region"] == after

    # 6. export edited review artifacts (from the edited manifest)
    rev = export_artifacts(ctx2.manifest, rd / "edited_review")
    stages["edited_review_export"] = bool(rev["artifacts"]["crops"])

    # 7. export the downstream package (editor manifest = source of truth)
    pkg_summary = build_package(ctx2.manifest, rd / "downstream_package",
                               source_manifest_path=str(ctx2.manifest_path))
    pkg = json.loads((rd / "downstream_package" / "package_manifest.json").read_text())
    assert validate_package(pkg) == [], "downstream package invalid"
    sem = pkg["source_editor_manifest"]
    stages["package_export"] = True
    stages["package_provenance_ok"] = sem.rsplit("/", 1)[-1] != "detected_manifest.json"
    stages["objects_jsonl"] = (rd / "downstream_package" / "objects.jsonl").exists()

    ok = all(stages.values())
    return {
        "ok": ok,
        "stages": stages,
        "object_edited": oid,
        "bbox_before": before, "bbox_after": after,
        "artifacts": {
            "detected_manifest": str(rd / "detected_manifest.json"),
            "editor_save_manifest": str(ctx2.manifest_path),
            "edited_review": str(rd / "edited_review"),
            "downstream_package": str(rd / "downstream_package"),
            "package_manifest": str(rd / "downstream_package" / "package_manifest.json"),
            "objects_jsonl": str(rd / "downstream_package" / "objects.jsonl"),
        },
        "package_objects": len(pkg["objects"]),
        "source_editor_manifest": sem,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Product end-to-end smoke (D28).")
    ap.add_argument("--pdf", required=True, help="input PDF to drive the end-to-end flow")
    ap.add_argument("--workdir", required=True, help="scratch dir for the run + exported artifacts")
    ap.add_argument("--json", action="store_true", help="emit the per-stage summary as pure JSON")
    args = ap.parse_args(argv)
    try:
        summary = run_e2e(args.pdf, args.workdir)
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        print(json.dumps(payload) if args.json else f"ERROR {exc}", file=(sys.stdout if args.json else sys.stderr))
        return 1
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("E2E OK" if summary["ok"] else "E2E FAILED")
        for k, v in summary["stages"].items():
            print(f"  {'✓' if v else '✗'} {k}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
