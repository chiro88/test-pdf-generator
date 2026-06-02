from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import CaseSpec, PageTruth


def case_truth_json(case: CaseSpec, pages: List[PageTruth]) -> Dict[str, Any]:
    return {
        "case_id": case.case_id,
        "axes": case.axes,
        "realistic": case.realistic,
        "coordinate_unit": "pdf_pt",
        "coordinate_origin": "top-left",
        "pages": [p.to_json() for p in pages],
    }


def write_truth(path: Path, truth: Dict[str, Any]) -> None:
    path.write_text(json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
