"""Axis coverage taxonomy and derivation for the RTM factory.

Coverage tags are derived *structurally* from the spec objects (PageSpec,
HeaderFooterSpec, WatermarkSpec, FigureSpec, TableSpec) rather than from
hand-written labels, so the coverage report cannot drift from what the
generated PDFs actually contain. A small set of non-structural tags (negative
scenario kinds, same-page fragments) is supplied per case via
``CaseSpec.coverage_hints``.

``AXIS_REQUIREMENTS`` is the single source of truth shared by the generator
(to build the MANIFEST coverage summary) and ``self_check`` (to fail the build
when a required axis value is under-covered).
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from .layout import page_dimensions

# group -> required axis values. Every value must appear in >= 2 cases unless
# listed in COVERAGE_EXCEPTIONS (which relaxes the minimum to 1). A required
# value that appears in 0 cases is always an error.
AXIS_REQUIREMENTS: Dict[str, List[str]] = {
    "page.size": ["letter", "a4"],
    "page.orientation": ["portrait", "landscape"],
    "page.columns": ["single", "two"],
    "page.pages": ["1", "3", "8"],
    "page.offset": ["zero", "nonzero"],
    "hf.mode": ["none", "header_only", "footer_only", "both"],
    "hf.variable": ["page_number", "subtitle"],
    "hf.mirrored": ["mirrored"],
    "hf.rule_line": ["rule_line"],
    "hf.partial": ["partial_support"],
    # D7 common-region realism axes
    "hf.rule": ["none", "header_rule", "footer_rule", "both_rules"],
    "hf.page_number_position": ["none", "bottom_center", "bottom_right", "page_x_of_y"],
    "hf.subtitle_position": ["none", "centered", "top_right"],
    "hf.support": ["all_pages", "first_page_suppressed", "partial_support"],
    "hf.jitter": ["none", "xy_jitter", "rule_y_jitter", "evenodd_jitter"],
    "wm.jitter": ["none", "position_jitter", "rotation_opacity_jitter", "variable_text_jitter", "near_footer"],
    "wm.presence": ["none", "fixed", "variable"],
    "wm.location": ["center", "corner"],
    "wm.opacity": ["light", "strong"],
    "wm.rotation": ["rot0", "diagonal"],
    "wm.image": ["image_like"],
    "fig.caption": ["above", "below"],
    "fig.alias": ["Figure", "Fig.", "FIGURE"],
    "fig.index": ["dotted", "integer", "dashed", "alpha"],
    "fig.title": ["one_line", "multiline"],
    "fig.body": ["waveform", "diagram", "raster", "mixed"],
    "fig.width": ["column", "page_wide"],
    "fig.count": ["multiple_per_page"],
    "tbl.span": ["single_page", "continuation"],
    "tbl.parts": ["2", "3", "4"],
    "tbl.suffix": ["(cont)", "(continued)", "continued", "Continued", "cont."],
    "tbl.title": ["same_title", "different_title"],
    "tbl.fragment": ["same_page_fragment"],
    "tbl.width": ["normal", "wide"],
    "tbl.caption": ["above"],
    "neg.kind": [
        "plain_text",
        "figure_of_merit",
        "see_table_above",
        "figure_ref_only",
        "table_ref_only",
        "weak_partial_header",
    ],
}

# Tags allowed to appear exactly once (rare one-off / presence-only), each with
# an explicit justification. Presence (count >= 1) is still required.
COVERAGE_EXCEPTIONS: Dict[str, str] = {
    "tbl.parts:4": "4-part continuation is a rare worst-case stress; one instance is sufficient.",
    "tbl.suffix:(continued)": "Continuation-marker presence check (handoff T2.7); one instance suffices.",
    "tbl.suffix:continued": "Continuation-marker presence check (handoff T2.7); one instance suffices.",
    "tbl.suffix:Continued": "Continuation-marker presence check (handoff T2.7); one instance suffices.",
    "tbl.suffix:cont.": "Continuation-marker presence check (handoff T2.7); one instance suffices.",
    "tbl.fragment:same_page_fragment": "Same-page split fragment is a rare layout; one instance suffices.",
    "neg.kind:plain_text": "Named negative scenario; presence-only by exact name.",
    "neg.kind:figure_of_merit": "Named negative scenario; presence-only by exact name.",
    "neg.kind:see_table_above": "Named negative scenario; presence-only by exact name.",
    "neg.kind:figure_ref_only": "Named negative scenario; presence-only by exact name.",
    "neg.kind:table_ref_only": "Named negative scenario; presence-only by exact name.",
    "neg.kind:weak_partial_header": "Named negative scenario; presence-only by exact name.",
    # D7 stress axes — single representative each is sufficient.
    "hf.rule:header_rule": "D7 header-rule realism variant; one representative.",
    "hf.rule:footer_rule": "D7 footer-rule realism variant; one representative.",
    "hf.rule:both_rules": "D7 both-rules realism variant; one representative.",
    "hf.page_number_position:bottom_right": "D7 page-number-position stress; one representative.",
    "hf.page_number_position:page_x_of_y": "D7 'Page x of y' stress; one representative.",
    "hf.subtitle_position:top_right": "D7 subtitle-position stress; one representative.",
    "hf.support:first_page_suppressed": "D7 first-page-suppression stress; one representative.",
    "hf.jitter:xy_jitter": "D7 per-page xy jitter stress; one representative.",
    "hf.jitter:rule_y_jitter": "D7 rule-y jitter stress; one representative.",
    "hf.jitter:evenodd_jitter": "D7 even/odd mirror + jitter stress; one representative.",
    "wm.jitter:position_jitter": "D7 watermark position jitter stress; one representative.",
    "wm.jitter:rotation_opacity_jitter": "D7 watermark rotation/opacity jitter stress; one representative.",
    "wm.jitter:variable_text_jitter": "D7 watermark variable-text + jitter stress; one representative.",
    "wm.jitter:near_footer": "D7 watermark-near-footer stress; one representative.",
}

STRONG_OPACITY_THRESHOLD = 0.22
PAGE_WIDE_RATIO = 0.85


def min_count(tag: str) -> int:
    return 1 if tag in COVERAGE_EXCEPTIONS else 2


def _index_style(index: str) -> str:
    if any(c.isalpha() for c in index):
        return "alpha"
    if "-" in index:
        return "dashed"
    if "." in index:
        return "dotted"
    return "integer"


def derive_tags(case: Any) -> List[str]:
    """Derive the structural coverage tags exhibited by one CaseSpec."""
    tags: Set[str] = set()
    page_w, _page_h = page_dimensions(case.page.size, case.page.orientation)

    # --- page axis -----------------------------------------------------------
    tags.add(f"page.size:{case.page.size}")
    tags.add(f"page.orientation:{case.page.orientation}")
    tags.add(f"page.columns:{'two' if case.page.columns == 2 else 'single'}")
    tags.add(f"page.pages:{case.page.page_count}")
    tags.add(f"page.offset:{'nonzero' if case.page.page_offset else 'zero'}")

    # --- header / footer axis ------------------------------------------------
    header, footer = case.header, case.footer
    if header.enabled and footer.enabled:
        mode = "both"
    elif header.enabled:
        mode = "header_only"
    elif footer.enabled:
        mode = "footer_only"
    else:
        mode = "none"
    tags.add(f"hf.mode:{mode}")
    for hf in (header, footer):
        if not hf.enabled:
            continue
        if "{page}" in hf.text_template:
            tags.add("hf.variable:page_number")
        if "{subtitle}" in hf.text_template:
            tags.add("hf.variable:subtitle")
        if hf.mirrored_even_odd:
            tags.add("hf.mirrored:mirrored")
        if hf.rule_line:
            tags.add("hf.rule_line:rule_line")
        if hf.support_pages is not None and len(hf.support_pages) < case.page.page_count:
            tags.add("hf.partial:partial_support")

    # --- D7 common-region realism axes ---------------------------------------
    enabled_hfs = [(s, s.kind or kk) for s, kk in
                   ([(header, "header"), (footer, "footer")] + [(e, e.kind or "footer") for e in case.extra_regions])
                   if s.enabled]
    rule_kinds = {kk for s, kk in enabled_hfs if s.rule_line}
    if {"header", "footer"} <= rule_kinds:
        tags.add("hf.rule:both_rules")
    elif "header" in rule_kinds:
        tags.add("hf.rule:header_rule")
    elif "footer" in rule_kinds:
        tags.add("hf.rule:footer_rule")
    else:
        tags.add("hf.rule:none")

    if enabled_hfs:
        if any(s.first_page_suppressed for s, _ in enabled_hfs):
            tags.add("hf.support:first_page_suppressed")
        elif any(s.support_pages is not None and len(s.support_pages) < case.page.page_count for s, _ in enabled_hfs):
            tags.add("hf.support:partial_support")
        else:
            tags.add("hf.support:all_pages")

    has_xy_jit = any(s.jitter_x or s.jitter_y for s, _ in enabled_hfs)
    has_rule_jit = any(s.rule_jitter_y for s, _ in enabled_hfs)
    has_evenodd_jit = any(s.mirrored_even_odd and (s.jitter_x or s.jitter_y) for s, _ in enabled_hfs)
    if has_xy_jit:
        tags.add("hf.jitter:xy_jitter")
    if has_rule_jit:
        tags.add("hf.jitter:rule_y_jitter")
    if has_evenodd_jit:
        tags.add("hf.jitter:evenodd_jitter")
    if not (has_xy_jit or has_rule_jit):
        tags.add("hf.jitter:none")

    if not any(h.startswith("hf.page_number_position:") for h in case.coverage_hints):
        pn = "none"
        for s, _ in enabled_hfs:
            if "{pages}" in s.text_template:
                pn = "page_x_of_y"
                break
            if "{page}" in s.text_template:
                pn = "bottom_center"
        tags.add(f"hf.page_number_position:{pn}")
    if not any(h.startswith("hf.subtitle_position:") for h in case.coverage_hints):
        sub = "centered" if any("{subtitle}" in s.text_template for s, _ in enabled_hfs) else "none"
        tags.add(f"hf.subtitle_position:{sub}")

    # --- watermark axis ------------------------------------------------------
    wm = case.watermark
    if not wm.enabled:
        tags.add("wm.presence:none")
    else:
        tags.add(f"wm.presence:{'variable' if wm.variable_text else 'fixed'}")
        tags.add(f"wm.location:{wm.location}")
        tags.add(f"wm.opacity:{'strong' if wm.opacity >= STRONG_OPACITY_THRESHOLD else 'light'}")
        tags.add(f"wm.rotation:{'diagonal' if abs(wm.rotation_deg) > 0.01 else 'rot0'}")
        if wm.image_like:
            tags.add("wm.image:image_like")
    # wm.jitter (D7): emitted for every case so 'none' is abundant
    if case.watermark.enabled and (case.watermark.jitter_pos or case.watermark.jitter_rot
                                   or case.watermark.jitter_opacity or case.watermark.near_footer):
        w = case.watermark
        if w.jitter_pos:
            tags.add("wm.jitter:position_jitter")
        if w.jitter_rot or w.jitter_opacity:
            tags.add("wm.jitter:rotation_opacity_jitter")
        if w.variable_text and (w.jitter_pos or w.jitter_rot or w.jitter_opacity):
            tags.add("wm.jitter:variable_text_jitter")
        if w.near_footer:
            tags.add("wm.jitter:near_footer")
    else:
        tags.add("wm.jitter:none")

    # --- figure axis ---------------------------------------------------------
    figs_by_page: Dict[int, int] = Counter()
    for fig in case.figures:
        figs_by_page[fig.page] += 1
        tags.add(f"fig.caption:{'above' if fig.caption_position == 'above' else 'below'}")
        tags.add(f"fig.alias:{fig.alias}")
        tags.add(f"fig.index:{_index_style(fig.index)}")
        tags.add(f"fig.title:{'multiline' if chr(10) in fig.title else 'one_line'}")
        tags.add(f"fig.body:{fig.body_template}")
        tags.add(f"fig.width:{'page_wide' if fig.body_region.width >= PAGE_WIDE_RATIO * page_w else 'column'}")
    if any(n >= 2 for n in figs_by_page.values()):
        tags.add("fig.count:multiple_per_page")

    # --- table axis ----------------------------------------------------------
    groups: Dict[str, list] = {}
    titles: List[str] = []
    for tbl in case.tables:
        groups.setdefault(tbl.table_group_id, []).append(tbl)
        titles.append(tbl.title)
        tags.add(f"tbl.width:{'wide' if tbl.body_region.width >= PAGE_WIDE_RATIO * page_w else 'normal'}")
        if tbl.caption_region.y0 < tbl.body_region.y0:
            tags.add("tbl.caption:above")
        if tbl.is_continuation and tbl.continuation_marker:
            tags.add(f"tbl.suffix:{tbl.continuation_marker}")
    for members in groups.values():
        is_cont = len(members) >= 2 or any(m.is_continuation for m in members)
        if is_cont:
            parts = max(len(members), max(m.part_index for m in members))
            tags.add("tbl.span:continuation")
            tags.add(f"tbl.parts:{min(parts, 4)}")
        else:
            tags.add("tbl.span:single_page")
    if len(titles) >= 2:
        if len(set(titles)) < len(titles):
            tags.add("tbl.title:same_title")
        if len(set(titles)) >= 2:
            tags.add("tbl.title:different_title")

    # --- explicit, non-structural hints (neg.kind, fragment, ...) ------------
    for hint in case.coverage_hints:
        tags.add(hint)

    return sorted(tags)


def count_tags(cases) -> Counter:
    counts: Counter = Counter()
    for case in cases:
        for tag in derive_tags(case):
            counts[tag] += 1
    return counts


def coverage_summary(cases) -> Dict[str, Any]:
    """Machine-readable coverage summary for MANIFEST.json."""
    counts = count_tags(cases)
    required: List[Dict[str, Any]] = []
    missing: List[str] = []
    below_min: List[str] = []
    for group, values in AXIS_REQUIREMENTS.items():
        for value in values:
            tag = f"{group}:{value}"
            cnt = counts.get(tag, 0)
            need = min_count(tag)
            required.append({"tag": tag, "count": cnt, "min": need})
            if cnt == 0:
                missing.append(tag)
            elif cnt < need:
                below_min.append(tag)
    return {
        "total_cases": len(cases),
        "counts": dict(sorted(counts.items())),
        "required": required,
        "missing": missing,
        "below_min": below_min,
        "exceptions": COVERAGE_EXCEPTIONS,
    }
