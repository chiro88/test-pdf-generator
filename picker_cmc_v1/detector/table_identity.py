"""Truth-blind table identity + continuation linking (D12).

A detector cannot read truth, so it derives a stable canonical table_group_id
from the caption index, links multipage / same-page continuation parts into one
group, and keeps independent same-index tables distinct.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .title_patterns import continuation_marker


def canonical_group_id(index: str) -> str:
    """'2.1'->tbl_002_001, '10.1'->tbl_010_001, '5-1'->tbl_005_001, 'A.1'->tbl_A_001."""
    parts = re.split(r"[.\-]", index)
    comps = [p.zfill(3) if p.isdigit() else p.upper() for p in parts if p != ""]
    return "tbl_" + "_".join(comps)


def _bump_last(group_id: str, occurrence: int) -> str:
    """Distinct id for an independent same-index table (occurrence>0)."""
    head, _, last = group_id.rpartition("_")
    if last.isdigit():
        return f"{head}_{int(last) + occurrence:03d}"
    return f"{group_id}_{occurrence + 1:03d}"


def assign_table_groups(table_anchors: List[Tuple[int, "Anchor"]]) -> Dict[int, dict]:
    """Map id(anchor) -> {group_id, part_index, is_continuation, continuation_marker}.

    table_anchors: (page, anchor) in reading order (page asc, then y asc).
    """
    by_index: Dict[str, List[Tuple[int, "Anchor"]]] = {}
    for pg, a in table_anchors:
        by_index.setdefault(a.index, []).append((pg, a))

    meta: Dict[int, dict] = {}
    for index, items in by_index.items():
        canon = canonical_group_id(index)
        markers = [continuation_marker(a.title) for _, a in items]
        is_continuation_group = len(items) > 1 and any(markers)
        if is_continuation_group:
            for part, (_, a) in enumerate(items, start=1):
                mk = continuation_marker(a.title) if part > 1 else None
                meta[id(a)] = {"group_id": canon, "part_index": part,
                               "is_continuation": part > 1, "continuation_marker": mk}
        else:
            for occ, (_, a) in enumerate(items):
                gid = canon if occ == 0 else _bump_last(canon, occ)
                meta[id(a)] = {"group_id": gid, "part_index": 1,
                               "is_continuation": False, "continuation_marker": None}
    return meta
