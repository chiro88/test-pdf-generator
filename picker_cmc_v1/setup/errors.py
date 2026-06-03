"""setup-yaml-v0 error codes (D22).

A single structured error type so the runner / future server can branch on a
stable code. SETUP_MISSING_FIELD is for an ABSENT required field; a field that is
present but wrong is SETUP_INVALID_VALUE.
"""
from __future__ import annotations

ERROR_CODES = (
    "SETUP_FILE_NOT_FOUND",          # the setup file path does not exist
    "SETUP_FILE_UNREADABLE",         # not readable / not valid YAML / not a mapping
    "SETUP_MISSING_FIELD",           # a required field is absent
    "SETUP_PLACEHOLDER_UNRESOLVED",  # a CHANGE_ME placeholder was left in
    "SETUP_INVALID_VALUE",           # a field is present but has an invalid value
    "SETUP_BAD_PAGE_RANGE",          # input.page_range is malformed
    "SETUP_UNKNOWN_DETECTOR",        # advanced_fine_tuning.detector_profile unknown
    "SETUP_UNKNOWN_TEMPLATE",        # requested setup template name unknown
)


class SetupError(Exception):
    """A setup-yaml-v0 contract violation, carrying a stable error code."""

    def __init__(self, code: str, message: str, field: str | None = None):
        assert code in ERROR_CODES, f"unknown setup error code {code!r}"
        self.code = code
        self.message = message
        self.field = field
        super().__init__(f"[{code}] {message}" + (f" (field: {field})" if field else ""))

    def to_dict(self) -> dict:
        out = {"ok": False, "error_code": self.code, "error": self.message}
        if self.field:
            out["field"] = self.field
        return out
