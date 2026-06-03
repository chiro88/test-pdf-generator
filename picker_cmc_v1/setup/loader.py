"""setup-yaml-v0 loader (D22): read the YAML file into a mapping, or raise."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .errors import SetupError


def load_setup(path: str | Path) -> Dict[str, Any]:
    """Load a setup YAML file into a dict. Raises SetupError with a file-level code."""
    p = Path(path)
    if not p.exists():
        raise SetupError("SETUP_FILE_NOT_FOUND", f"setup file not found: {p}")
    try:
        import yaml
        text = p.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except Exception as exc:                       # unreadable file / invalid YAML
        raise SetupError("SETUP_FILE_UNREADABLE", f"cannot read setup YAML {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise SetupError("SETUP_FILE_UNREADABLE", "setup YAML root must be a mapping")
    return data
