"""D23 web-editor run context (read-only).

Loads a run directory into a RunContext the server serves. Prefers an
editor-save-manifest-v0 (validated before serving); falls back to building one from
a detector-output-v0 manifest. The editor-save-manifest is the view source.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
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

    @property
    def pages(self) -> List[Dict[str, Any]]:
        return self.manifest.get("pages", [])

    @property
    def page_count(self) -> int:
        return len(self.pages)


def load_run(run_dir: str | Path) -> RunContext:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise WebEditorError("RUN_DIR_NOT_FOUND", f"run directory not found: {run_dir}")

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

    return RunContext(run_dir=run_dir, source_pdf=manifest.get("source_pdf", ""),
                      manifest=manifest, manifest_path=manifest_path)
