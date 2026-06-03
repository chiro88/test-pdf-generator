"""D23 web-editor run context (read-only).

Loads a run directory into a RunContext the server serves. Prefers an
editor-save-manifest-v0 (validated before serving); falls back to building one from
a detector-output-v0 manifest. The editor-save-manifest is the view source.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from editor_manifest import writer as save_writer
from editor_manifest.validator import validate_manifest as validate_editor

RUN_SCHEMA_VERSION = "web-editor-run-v0"


class WebEditorError(Exception):
    """A web-editor run-load failure, carrying a stable error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> dict:
        return {"ok": False, "error_code": self.code, "error": self.message}


@dataclass
class RunContext:
    run_dir: Path
    source_pdf: str
    manifest: Dict[str, Any]          # editor-save-manifest-v0 (view source)
    manifest_path: Path
    save_path: Path                   # where Save writes (editor_save_manifest.json)
    page_sizes: Dict[int, tuple] = field(default_factory=dict)  # page -> (w, h) pt
    dirty: bool = False               # unsaved edits in memory

    @property
    def pages(self) -> List[Dict[str, Any]]:
        return self.manifest.get("pages", [])

    @property
    def page_count(self) -> int:
        return len(self.pages)


def load_run(run_dir: str | Path, manifest_path: str | Path | None = None) -> RunContext:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise WebEditorError("RUN_DIR_NOT_FOUND", f"run directory not found: {run_dir}")

    # D25: an explicit editor-save-manifest path (e.g. a Save-As version). Policy:
    # it must live inside the run directory (the same write/read boundary).
    if manifest_path is not None:
        mp = Path(manifest_path)
        run_root, target = run_dir.resolve(), mp.resolve()
        if run_root != target and run_root not in target.parents:
            raise WebEditorError("MANIFEST_OUTSIDE_RUN_DIR",
                                 f"manifest must be inside the run directory: {mp}")
        if not mp.exists():
            raise WebEditorError("RUN_MANIFEST_NOT_FOUND", f"manifest not found: {mp}")
        try:
            manifest = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WebEditorError("RUN_MANIFEST_UNREADABLE", f"cannot read {mp}: {exc}") from exc
        errors = validate_editor(manifest)
        if errors:
            raise WebEditorError("RUN_MANIFEST_INVALID", "; ".join(errors[:3]))
        return _finish(run_dir, manifest, mp, save_path=mp)

    em = run_dir / "editor_save_manifest.json"
    dm = run_dir / "detected_manifest.json"

    if em.exists():
        try:
            manifest = json.loads(em.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WebEditorError("RUN_MANIFEST_UNREADABLE", f"cannot read {em}: {exc}") from exc
        errors = validate_editor(manifest)
        if errors:                                  # enforce the contract BEFORE serving
            raise WebEditorError("RUN_MANIFEST_INVALID", "; ".join(errors[:3]))
        manifest_path = em
    elif dm.exists():
        try:
            det = json.loads(dm.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WebEditorError("RUN_MANIFEST_UNREADABLE", f"cannot read {dm}: {exc}") from exc
        src = det["cases"][0]["pdf"] if det.get("cases") else ""
        manifest = save_writer.build_initial(det, source_pdf=src, source_detector_manifest=str(dm))
        manifest_path = dm
    else:
        raise WebEditorError("RUN_MANIFEST_NOT_FOUND",
                             f"no editor_save_manifest.json or detected_manifest.json in {run_dir}")

    return _finish(run_dir, manifest, manifest_path, save_path=run_dir / "editor_save_manifest.json")


def _finish(run_dir: Path, manifest: Dict[str, Any], manifest_path: Path, save_path: Path) -> RunContext:
    source_pdf = manifest.get("source_pdf", "")
    page_sizes: Dict[int, tuple] = {}
    if source_pdf and Path(source_pdf).exists():
        try:
            import fitz
            doc = fitz.open(source_pdf)
            for i in range(doc.page_count):
                page_sizes[i + 1] = (doc[i].rect.width, doc[i].rect.height)
            doc.close()
        except Exception:
            page_sizes = {}                          # bounds check simply skipped
    return RunContext(run_dir=run_dir, source_pdf=source_pdf, manifest=manifest,
                      manifest_path=manifest_path, save_path=save_path, page_sizes=page_sizes)
