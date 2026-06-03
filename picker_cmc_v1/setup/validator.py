"""setup-yaml-v0 validator (D22).

Distinguishes an ABSENT required field (SETUP_MISSING_FIELD) from a present but
wrong value (SETUP_INVALID_VALUE), and flags unresolved CHANGE_ME placeholders.
"""
from __future__ import annotations

import re
from typing import Any, Dict

from . import schema
from .errors import SetupError

_PAGE_RANGE_RE = re.compile(r"^\s*\d+\s*(-\s*\d+\s*)?$")

_SENTINEL = object()


def _dig(data: Dict[str, Any], dotted: str):
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _SENTINEL
        cur = cur[part]
    return cur


def validate_setup(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a parsed setup mapping; return it on success, else raise SetupError."""
    # schema_version: absent -> MISSING; present but wrong -> INVALID_VALUE
    sv = _dig(data, "schema_version")
    if sv is _SENTINEL:
        raise SetupError("SETUP_MISSING_FIELD", "schema_version is required", field="schema_version")
    if sv != schema.SCHEMA_VERSION:
        raise SetupError("SETUP_INVALID_VALUE",
                         f"schema_version must be {schema.SCHEMA_VERSION!r} (got {sv!r})", field="schema_version")

    for path in schema.REQUIRED_FIELDS:
        if path == "schema_version":
            continue
        v = _dig(data, path)
        if v is _SENTINEL:
            raise SetupError("SETUP_MISSING_FIELD", f"{path} is required", field=path)
        if not isinstance(v, str) or not v.strip():
            raise SetupError("SETUP_INVALID_VALUE", f"{path} must be a non-empty string", field=path)

    for path in schema.PLACEHOLDER_FIELDS:
        v = _dig(data, path)
        if isinstance(v, str) and v.strip() == schema.PLACEHOLDER:
            raise SetupError("SETUP_PLACEHOLDER_UNRESOLVED",
                             f"{path} still has the {schema.PLACEHOLDER} placeholder", field=path)

    # optional page_range
    pr = _dig(data, "input.page_range")
    if pr is not _SENTINEL and pr is not None:
        if not isinstance(pr, str) or not _PAGE_RANGE_RE.match(pr):
            raise SetupError("SETUP_BAD_PAGE_RANGE",
                             f"input.page_range must look like '1-5' or '3' (got {pr!r})", field="input.page_range")
        lo, _, hi = pr.partition("-")
        if hi and int(hi) < int(lo):
            raise SetupError("SETUP_BAD_PAGE_RANGE", f"input.page_range end < start ({pr!r})", field="input.page_range")

    adv = _dig(data, "advanced_fine_tuning")
    adv = adv if isinstance(adv, dict) else {}
    profile = adv.get("detector_profile", "default")
    if profile not in schema.VALID_DETECTOR_PROFILES:
        raise SetupError("SETUP_UNKNOWN_DETECTOR",
                         f"unknown detector_profile {profile!r} (known: {schema.VALID_DETECTOR_PROFILES})",
                         field="advanced_fine_tuning.detector_profile")
    cu = adv.get("coordinate_unit", "pdf_pt")
    if cu not in schema.VALID_COORDINATE_UNITS:
        raise SetupError("SETUP_INVALID_VALUE", f"coordinate_unit must be one of {schema.VALID_COORDINATE_UNITS}",
                         field="advanced_fine_tuning.coordinate_unit")
    co = adv.get("coordinate_origin", "top-left")
    if co not in schema.VALID_COORDINATE_ORIGINS:
        raise SetupError("SETUP_INVALID_VALUE", f"coordinate_origin must be one of {schema.VALID_COORDINATE_ORIGINS}",
                         field="advanced_fine_tuning.coordinate_origin")
    return data
