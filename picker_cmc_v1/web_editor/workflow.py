"""D26 setup-YAML web workflow helpers (parse / validate / run-from-setup).

Shared by the CLI and the web API so a browser can download a template, validate a
setup, and create a detector run without touching the detector itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from detector.pipeline import detect_pdf
from detector_output import writer as det_writer
from editor_manifest import writer as save_writer
from setup.errors import SetupError
from setup.loader import load_setup
from setup.validator import validate_setup


def parse_setup(body: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a setup mapping from {setup_path} or inline {setup_yaml}. Raises SetupError."""
    if body.get("setup_path"):
        return load_setup(body["setup_path"])
    text = body.get("setup_yaml")
    if not text or not isinstance(text, str):
        raise SetupError("SETUP_FILE_UNREADABLE", "provide setup_path or setup_yaml")
    try:
        import yaml
        data = yaml.safe_load(text)
    except Exception as exc:
        raise SetupError("SETUP_FILE_UNREADABLE", f"invalid setup YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SetupError("SETUP_FILE_UNREADABLE", "setup YAML root must be a mapping")
    return data


def run_from_setup(setup: Dict[str, Any]) -> Path:
    """Validate a setup, run the detector, write the manifests; return the run dir.

    Raises SetupError (invalid setup) — never tunes the detector.
    """
    cfg = validate_setup(setup)
    pdf_path = cfg["input"]["pdf_path"]
    if not Path(pdf_path).exists():
        raise SetupError("SETUP_INVALID_VALUE", f"input.pdf_path not found: {pdf_path}", field="input.pdf_path")
    out_dir = Path(cfg["output"]["artifact_dir"])
    name = cfg["project"]["name"]

    detection = detect_pdf(pdf_path)
    manifest = det_writer.build_manifest([det_writer.case(name, str(pdf_path), detection["pages"])],
                                         name="picker_cmc", mode="detector")
    det_path = det_writer.write_manifest(out_dir / "detected_manifest.json", manifest)
    save_path = Path(cfg["output"].get("save_manifest_path") or (out_dir / "editor_save_manifest.json"))
    save = save_writer.build_initial(manifest, source_pdf=str(pdf_path), source_detector_manifest=str(det_path))
    save_writer.write_manifest(save_path, save)
    return out_dir
