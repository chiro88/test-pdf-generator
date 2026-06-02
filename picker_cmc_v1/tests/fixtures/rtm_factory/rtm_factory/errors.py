"""Structured error codes + exit-code mapping for the RTM CLI (D5.5).

Exit codes:
  0 = success
  1 = command completed but validation/comparison failed
  2 = invalid input / schema / unreadable file
  3 = internal generation/rendering failure
"""
from __future__ import annotations

from typing import Any, List, Optional

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INVALID_INPUT = 2
EXIT_INTERNAL = 3

# error_code -> exit code
ERROR_EXIT = {
    "SCENARIO_FILE_NOT_FOUND": EXIT_INVALID_INPUT,
    "SCENARIO_FILE_UNREADABLE": EXIT_INVALID_INPUT,
    "SCENARIO_INVALID_VALUE": EXIT_INVALID_INPUT,
    "SCENARIO_UNKNOWN_TEMPLATE": EXIT_INVALID_INPUT,
    "SCENARIO_BAD_BBOX": EXIT_INVALID_INPUT,
    "SCENARIO_OUT_OF_PAGE_BOUNDS": EXIT_INVALID_INPUT,
    "SCENARIO_UNSUPPORTED_PAGE_SIZE": EXIT_INVALID_INPUT,
    "OUTPUT_DIR_EXISTS": EXIT_INVALID_INPUT,
    "INVALID_INPUT": EXIT_INVALID_INPUT,
    "SELF_CHECK_FAILED": EXIT_FAILED,
    "PROMOTION_FAILED": EXIT_FAILED,
    "COMPARE_FAILED": EXIT_FAILED,
    "PDF_GENERATION_FAILED": EXIT_INTERNAL,
    "OVERLAY_FAILED": EXIT_INTERNAL,
}


class RtmError(Exception):
    """A CLI error with a stable error_code and optional field/allowed_values."""

    def __init__(self, error_code: str, message: str, *, field: Optional[str] = None,
                 allowed_values: Optional[List[Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.field = field
        self.allowed_values = allowed_values

    @property
    def exit_code(self) -> int:
        return ERROR_EXIT.get(self.error_code, EXIT_INVALID_INPUT)

    def to_json(self) -> dict:
        out = {"ok": False, "error_code": self.error_code, "message": self.message}
        if self.field is not None:
            out["field"] = self.field
        if self.allowed_values is not None:
            out["allowed_values"] = self.allowed_values
        return out
