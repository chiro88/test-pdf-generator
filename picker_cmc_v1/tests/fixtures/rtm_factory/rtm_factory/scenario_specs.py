from __future__ import annotations

from typing import List, Tuple

from .layout import band
from .models import (
    CaseSpec,
    FigureSpec,
    HeaderFooterSpec,
    NegativeTextSpec,
    PageSpec,
    TableSpec,
    WatermarkSpec,
)
from .sequence import SequenceBuilder
from .templates import FOOTER_TEMPLATES, HEADER_TEMPLATES, WATERMARK_TEMPLATES


def _hf_header(rule: bool = True, mirrored: bool = False, support_pages=None) -> HeaderFooterSpec:
    return HeaderFooterSpec(
        enabled=True,
        bbox=band(48, 18, 564, 54),
        text_template=HEADER_TEMPLATES["subtitle_page"],
        variable_text=True,
        mirrored_even_odd=mirrored,
        rule_line=rule,
        support_pages=support_pages,
    )


def _hf_footer(rule: bool = True, mirrored: bool = False, support_pages=None) -> HeaderFooterSpec:
    return HeaderFooterSpec(
        enabled=True,
        bbox=band(48, 740, 564, 774),
        text_template=FOOTER_TEMPLATES["confidential_page"],
        variable_text=True,
        mirrored_even_odd=mirrored,
        rule_line=rule,
        support_pages=support_pages,
    )


# --- spec construction helpers (keep scenario data declarative) --------------


def _figure(
    index: str,
    title: str,
    *,
    body_kind: str = "waveform",
    alias: str = "Figure",
    pos: str = "below",
    x0: float = 54.0,
    x1: float = 558.0,
    top: float = 170.0,
    body_h: float = 300.0,
    cap_h: float = 26.0,
    gap: float = 10.0,
    page: int = 1,
) -> FigureSpec:
    """Build a FigureSpec from a single anchor, deriving caption/body bands."""
    if pos == "below":
        body_box = band(x0, top, x1, top + body_h)
        cap_box = band(x0, top + body_h + gap, x1, top + body_h + gap + cap_h)
    else:  # caption above body
        cap_box = band(x0, top, x1, top + cap_h)
        body_box = band(x0, top + cap_h + gap, x1, top + cap_h + gap + body_h)
    return FigureSpec(
        index,
        title,
        cap_box,
        body_box,
        body_template=body_kind,
        alias=alias,
        caption_position=pos,
        page=page,
    )


def _table(
    index: str,
    title: str,
    group: str,
    *,
    x0: float = 54.0,
    x1: float = 558.0,
    top: float = 100.0,
    body_h: float = 560.0,
    cap_h: float = 26.0,
    gap: float = 10.0,
    part: int = 1,
    cont: bool = False,
    marker=None,
    page: int = 1,
    cont_from=None,
    rows: int = 8,
    cols: int = 4,
) -> TableSpec:
    """Build a TableSpec with caption above body, deriving the two bands."""
    cap_box = band(x0, top, x1, top + cap_h)
    body_box = band(x0, top + cap_h + gap, x1, top + cap_h + gap + body_h)
    return TableSpec(
        index,
        title,
        cap_box,
        body_box,
        group,
        part_index=part,
        is_continuation=cont,
        continuation_marker=marker,
        page=page,
        continued_from=cont_from,
        rows=rows,
        cols=cols,
    )


def _continuation(
    index: str,
    title: str,
    group: str,
    marker: str,
    parts: int,
    *,
    body_h: float = 620.0,
    rows: int = 10,
    cols: int = 4,
) -> Tuple[TableSpec, ...]:
    """One continuation table group spread across ``parts`` pages (one part/page)."""
    specs = []
    for p in range(1, parts + 1):
        specs.append(
            _table(
                index,
                title,
                group,
                part=p,
                cont=(p > 1),
                marker=(marker if p > 1 else None),
                page=p,
                cont_from=(group if p > 1 else None),
                body_h=body_h,
                rows=rows,
                cols=cols,
            )
        )
    return tuple(specs)


def core_cases() -> List[CaseSpec]:
    return [
        CaseSpec(
            case_id="core_fixed_header_footer",
            axes={"core": "fixed_header_footer", "header_footer": "both_fixed", "pages": 3, "columns": "single"},
            page=PageSpec(page_count=3),
            header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["plain"], False, False, True),
            footer=HeaderFooterSpec(True, band(48, 740, 564, 774), FOOTER_TEMPLATES["plain"], False, False, True),
            notes="Fixed header and footer appear on every page with stable y-bands.",
        ),
        CaseSpec(
            case_id="core_variable_subtitle_header",
            axes={"core": "variable_subtitle_header", "header_footer": "header_variable_subtitle", "pages": 3, "page_offset": 10},
            page=PageSpec(page_count=3, page_offset=10),
            header=_hf_header(rule=True, mirrored=True),
            notes="Header keeps stable position but text varies by page/subtitle and even/odd mirroring.",
        ),
        CaseSpec(
            case_id="core_fixed_watermark",
            axes={"core": "fixed_watermark", "watermark": "center_rot45_fixed", "pages": 1},
            page=PageSpec(page_count=1),
            watermark=WatermarkSpec(True, band(140, 300, 470, 500), WATERMARK_TEMPLATES["confidential"], False, 45, 0.16, "center"),
            notes="Centered diagonal fixed text watermark.",
        ),
        CaseSpec(
            case_id="core_figure_caption_bottom",
            axes={"core": "figure_caption_bottom", "figure": "caption_below_body", "index": "3.4", "body": "waveform"},
            page=PageSpec(page_count=1),
            figures=(FigureSpec("3.4", "Waveform timing relationship", band(54, 492, 558, 520), band(54, 210, 558, 485), "waveform", "Figure", "below"),),
            notes="Figure body above caption; expected figure_body_direction=up.",
        ),
        CaseSpec(
            case_id="core_figure_caption_top",
            axes={"core": "figure_caption_top", "figure": "caption_above_body", "index": "A.1", "body": "diagram"},
            page=PageSpec(page_count=1),
            figures=(FigureSpec("A.1", "Reset path block diagram", band(54, 126, 558, 154), band(54, 165, 558, 430), "diagram", "Fig.", "above"),),
            notes="Figure caption above body; alpha index protects ID formatting regressions.",
        ),
        CaseSpec(
            case_id="core_multipage_table_cont",
            axes={"core": "multipage_table_cont", "table": "continuation_3parts", "suffix": "(cont)", "pages": 3},
            page=PageSpec(page_count=3),
            header=_hf_header(),
            footer=_hf_footer(),
            tables=(
                TableSpec("2.1", "Register map", band(54, 90, 558, 118), band(54, 128, 558, 710), "tbl_002_001", 1, False, None, 1),
                TableSpec("2.1", "Register map", band(54, 90, 558, 118), band(54, 128, 558, 710), "tbl_002_001", 2, True, "(cont)", 2, "tbl_002_001"),
                TableSpec("2.1", "Register map", band(54, 90, 558, 118), band(54, 128, 558, 710), "tbl_002_001", 3, True, "(cont)", 3, "tbl_002_001"),
            ),
            notes="Three-page table continuation with identical title and continuation suffix.",
        ),
        CaseSpec(
            case_id="core_same_title_tables",
            axes={"core": "same_title_tables", "table": "same_title_distinct_groups", "pages": 1},
            page=PageSpec(page_count=1),
            tables=(
                # D12.5: independent same-index tables use occurrence-based canonical ids.
                TableSpec("4.2", "Electrical characteristics", band(54, 96, 558, 120), band(54, 130, 558, 310), "tbl_004_002", page=1, rows=5),
                TableSpec("4.2", "Electrical characteristics", band(54, 390, 558, 414), band(54, 424, 558, 650), "tbl_004_003", page=1, rows=6),
            ),
            notes="Two separate tables with the same visible title on the same page.",
        ),
        CaseSpec(
            case_id="core_wide_diagram_xrange",
            axes={"core": "wide_diagram_xrange", "figure": "wide_page_body", "columns": "two"},
            page=PageSpec(columns=2),
            figures=(FigureSpec("2-7", "Page-wide datapath overview", band(54, 500, 558, 528), band(40, 170, 572, 492), "mixed", "FIGURE", "below"),),
            notes="Page-wide figure across a two-column text texture; stresses x-range envelope.",
        ),
    ]


def negative_cases() -> List[CaseSpec]:
    return [
        CaseSpec(
            case_id="neg_plain_text_only",
            axes={"negative": "ordinary_text_no_regions", "pages": 1},
            page=PageSpec(page_count=1),
            realistic=True,
            notes="Plain engineering prose page with no common regions, figures, or tables.",
            coverage_hints=("neg.kind:plain_text",),
        ),
        CaseSpec(
            case_id="neg_false_figure_of_merit",
            axes={"negative": "figure_of_merit_phrase"},
            page=PageSpec(page_count=1),
            negative_texts=(NegativeTextSpec("Figure of merit is defined as the ratio of useful output to input power. This is not a caption.", band(70, 160, 540, 230)),),
            notes="Contains 'Figure' at sentence start but no figure object.",
            coverage_hints=("neg.kind:figure_of_merit",),
        ),
        CaseSpec(
            case_id="neg_false_see_table_above",
            axes={"negative": "see_table_above_phrase"},
            page=PageSpec(page_count=1),
            negative_texts=(NegativeTextSpec("For configuration details, see Table above in the previous section. No table appears on this page.", band(70, 240, 540, 310)),),
            notes="Contains table-like wording but no table title/body.",
            coverage_hints=("neg.kind:see_table_above",),
        ),
        CaseSpec(
            case_id="neg_caption_reference_only",
            axes={"negative": "caption_reference_only"},
            page=PageSpec(page_count=1),
            negative_texts=(NegativeTextSpec("Figure 3.4 is referenced for historical context only; the actual diagram is not reproduced here.", band(70, 180, 540, 260)),),
            notes="Looks like a caption prefix but is an inline reference only.",
            coverage_hints=("neg.kind:figure_ref_only",),
        ),
        CaseSpec(
            case_id="neg_false_table_reference",
            axes={"negative": "table_reference_only"},
            page=PageSpec(page_count=1),
            negative_texts=(NegativeTextSpec("Table 2.1 describes the legacy configuration in an earlier revision; that table is not reproduced on this page.", band(70, 200, 540, 280)),),
            notes="Inline 'Table 2.1' reference with no table title/body present.",
            coverage_hints=("neg.kind:table_ref_only",),
        ),
        CaseSpec(
            case_id="neg_weak_partial_header",
            axes={"negative": "weak_partial_header", "header_footer": "partial_support"},
            page=PageSpec(page_count=3),
            header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["subtitle_page"], True, False, False, support_pages=[1]),
            notes="Header-like text appears on only one of three pages; should test min support ratio behavior.",
            coverage_hints=("neg.kind:weak_partial_header",),
        ),
    ]


def expanded_cases() -> List[CaseSpec]:
    """Deterministic representative covering set (handoff T1).

    Cases are grouped by the coverage gap they primarily fill, but most carry
    several axis values at once. ``coverage.py`` derives the actual tags from
    these specs; ``self_check`` fails the build if any required axis value is
    under-covered.
    """
    cases: List[CaseSpec] = []

    # --- baseline v0 expansion (kept) ---------------------------------------
    cases.append(CaseSpec(
        case_id="exp_a4_landscape_footer_only_wm_corner",
        axes={"page_size": "a4", "orientation": "landscape", "footer": "only", "watermark": "corner_image_like"},
        page=PageSpec(size="a4", orientation="landscape", page_count=1),
        footer=HeaderFooterSpec(True, band(54, 520, 788, 555), FOOTER_TEMPLATES["doc_rev_page"], True, False, True),
        watermark=WatermarkSpec(True, band(585, 70, 780, 180), WATERMARK_TEMPLATES["draft"], False, 0, 0.12, "corner", True),
        notes="A4 landscape with footer-only common region and corner image-like watermark.",
    ))
    cases.append(CaseSpec(
        case_id="exp_two_column_multi_figures",
        axes={"columns": "two", "figure": "multiple_per_page", "labels": "Figure_and_Fig"},
        page=PageSpec(columns=2),
        figures=(
            FigureSpec("12", "Column-local waveform", band(54, 280, 286, 306), band(54, 140, 286, 272), "waveform", "Figure", "below"),
            FigureSpec("A.1", "Column-local raster map", band(326, 280, 558, 306), band(326, 140, 558, 272), "raster", "Fig.", "below"),
        ),
        notes="Two figures on one two-column page with different aliases and index styles.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_suffix_continued_lower",
        axes={"table": "continuation_2parts", "suffix": "continued"},
        page=PageSpec(page_count=2),
        tables=_continuation("5.3", "Timing limits", "tbl_005_003", "continued", 2),
        notes="Continuation suffix uses lowercase 'continued'.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_suffix_cont_dot",
        axes={"table": "continuation_2parts", "suffix": "cont."},
        page=PageSpec(page_count=2),
        tables=_continuation("6.1", "Pin configuration", "tbl_006_001", "cont.", 2),
        notes="Continuation suffix uses 'cont.' punctuation.",
    ))
    cases.append(CaseSpec(
        case_id="exp_caption_above_table_wide",
        axes={"table": "single_page_wide", "caption": "above", "width": "wide"},
        page=PageSpec(page_count=1),
        tables=(TableSpec("7.9", "Wide timing matrix", band(36, 105, 576, 130), band(36, 140, 576, 430), "tbl_007_009", rows=7, cols=7),),
        notes="Wide table with title above body.",
    ))
    cases.append(CaseSpec(
        case_id="exp_variable_watermark_email",
        axes={"watermark": "variable_email_rot45", "pages": 3},
        page=PageSpec(page_count=3),
        watermark=WatermarkSpec(True, band(120, 310, 500, 510), WATERMARK_TEMPLATES["licensed"], True, -45, 0.12, "center"),
        notes="Variable email watermark text at stable position across pages.",
    ))

    # --- page size / orientation / columns / pages / offset -----------------
    cases.append(CaseSpec(
        case_id="exp_a4_portrait_header_only",
        axes={"page_size": "a4", "orientation": "portrait", "header": "only"},
        page=PageSpec(size="a4", orientation="portrait", page_count=1),
        header=_hf_header(),
        notes="A4 portrait page with a header-only common region and rule line.",
    ))
    cases.append(CaseSpec(
        case_id="exp_letter_landscape_figure_pagewide",
        axes={"orientation": "landscape", "columns": "two", "figure": "page_wide_mixed"},
        page=PageSpec(orientation="landscape", columns=2, page_count=1),
        figures=(_figure("2-7", "Landscape datapath overview", body_kind="mixed", alias="FIGURE", pos="below", x0=40, x1=752, top=110, body_h=300),),
        notes="Letter landscape two-column page with a page-wide mixed figure.",
    ))
    cases.append(CaseSpec(
        case_id="exp_8page_mirror_hf",
        axes={"pages": 8, "header_footer": "both_mirrored", "page_offset": 5},
        page=PageSpec(page_count=8, page_offset=5),
        header=_hf_header(mirrored=True),
        footer=_hf_footer(mirrored=True),
        notes="Eight-page document with mirrored even/odd header and footer and a non-zero page offset.",
    ))
    cases.append(CaseSpec(
        case_id="exp_8page_watermark_strong",
        axes={"pages": 8, "watermark": "center_strong_rot0"},
        page=PageSpec(page_count=8),
        watermark=WatermarkSpec(True, band(150, 300, 460, 470), WATERMARK_TEMPLATES["confidential"], False, 0, 0.30, "center"),
        notes="Eight-page document with a strong-opacity centered upright watermark.",
    ))
    cases.append(CaseSpec(
        case_id="exp_nonzero_offset_footer",
        axes={"pages": 3, "page_offset": 100, "footer": "only"},
        page=PageSpec(page_count=3, page_offset=100),
        footer=_hf_footer(),
        notes="Footer-only document whose page numbers start at a large non-zero offset.",
    ))

    # --- header / footer variants -------------------------------------------
    cases.append(CaseSpec(
        case_id="exp_header_only_mirror",
        axes={"header": "only", "mirrored": "even_odd", "pages": 3},
        page=PageSpec(page_count=3),
        header=_hf_header(mirrored=True),
        notes="Header-only document with even/odd mirrored placement and variable subtitle/page text.",
    ))
    cases.append(CaseSpec(
        case_id="exp_footer_partial_support",
        axes={"footer": "only", "header_footer": "partial_support", "pages": 3},
        page=PageSpec(page_count=3),
        footer=HeaderFooterSpec(True, band(48, 740, 564, 774), FOOTER_TEMPLATES["confidential_page"], True, False, True, support_pages=[1, 3]),
        notes="Footer present on only two of three pages; exercises partial support ratio.",
    ))

    # --- watermark variants -------------------------------------------------
    cases.append(CaseSpec(
        case_id="exp_watermark_corner_rot0_light",
        axes={"watermark": "corner_rot0_light"},
        page=PageSpec(page_count=1),
        watermark=WatermarkSpec(True, band(400, 80, 560, 180), WATERMARK_TEMPLATES["draft"], False, 0, 0.12, "corner", False),
        notes="Light upright text watermark anchored in a page corner.",
    ))
    cases.append(CaseSpec(
        case_id="exp_watermark_strong_diagonal_corner",
        axes={"watermark": "corner_strong_rot45_variable"},
        page=PageSpec(page_count=1),
        watermark=WatermarkSpec(True, band(360, 60, 572, 260), WATERMARK_TEMPLATES["licensed"], True, 45, 0.32, "corner"),
        notes="Strong-opacity variable diagonal watermark anchored toward a corner.",
    ))
    cases.append(CaseSpec(
        case_id="exp_watermark_image_center",
        axes={"watermark": "center_image_like"},
        page=PageSpec(page_count=1),
        watermark=WatermarkSpec(True, band(150, 320, 460, 470), WATERMARK_TEMPLATES["confidential"], False, 0, 0.12, "center", True),
        notes="Centered image-like watermark (box + cross strokes) at light opacity.",
    ))

    # --- figure variants ----------------------------------------------------
    cases.append(CaseSpec(
        case_id="exp_figure_above_diagram_dotted",
        axes={"figure": "caption_above_diagram", "index": "3.4", "title": "multiline"},
        page=PageSpec(page_count=1),
        figures=(_figure("3.4", "Reset and clock distribution\nacross multiple power domains", body_kind="diagram", alias="Figure", pos="above", top=120, body_h=300, cap_h=46),),
        notes="Figure with a multiline caption above a block diagram body.",
    ))
    cases.append(CaseSpec(
        case_id="exp_figure_integer_waveform",
        axes={"figure": "integer_index_waveform", "index": "12", "alias": "FIGURE"},
        page=PageSpec(page_count=1),
        figures=(_figure("12", "Sampled output waveform", body_kind="waveform", alias="FIGURE", pos="below", top=180, body_h=300),),
        notes="Integer figure index with uppercase FIGURE alias and waveform body.",
    ))
    cases.append(CaseSpec(
        case_id="exp_figure_multi_raster_multiline",
        axes={"figure": "multiple_per_page", "title": "multiline", "body": "raster_and_diagram"},
        page=PageSpec(page_count=1),
        figures=(
            _figure("A.1", "Die photo raster map\nwith annotated blocks", body_kind="raster", alias="Fig.", pos="below", top=110, body_h=160, cap_h=46),
            _figure("3.4", "Floorplan block diagram\nof the analog front end", body_kind="diagram", alias="Figure", pos="below", top=400, body_h=160, cap_h=46),
        ),
        notes="Two figures on one page, both with multiline titles and different body kinds.",
    ))
    cases.append(CaseSpec(
        case_id="exp_figure_pagewide_raster",
        axes={"figure": "page_wide_raster", "index": "2-7"},
        page=PageSpec(page_count=1),
        figures=(_figure("2-7", "Page-wide thermal raster", body_kind="raster", alias="Figure", pos="below", x0=40, x1=572, top=170, body_h=320),),
        notes="Page-wide raster figure spanning nearly the full text width.",
    ))

    # --- table variants -----------------------------------------------------
    cases.append(CaseSpec(
        case_id="exp_table_continued_paren",
        axes={"table": "continuation_2parts", "suffix": "(continued)"},
        page=PageSpec(page_count=2),
        tables=_continuation("8.2", "Absolute maximum ratings", "tbl_008_002", "(continued)", 2),
        notes="Continuation suffix uses parenthesized '(continued)'.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_continued_cap",
        axes={"table": "continuation_2parts", "suffix": "Continued"},
        page=PageSpec(page_count=2),
        tables=_continuation("9.4", "Recommended operating conditions", "tbl_009_004", "Continued", 2),
        notes="Continuation suffix uses capitalized 'Continued'.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_3part_cont",
        axes={"table": "continuation_3parts", "suffix": "(cont)"},
        page=PageSpec(page_count=3),
        tables=_continuation("10.1", "Memory map", "tbl_010_001", "(cont)", 3),
        notes="Three-part table continuation, distinct group from the core continuation case.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_4part_cont",
        axes={"table": "continuation_4parts", "suffix": "(cont)"},
        page=PageSpec(page_count=4),
        tables=_continuation("11.5", "Interrupt vector table", "tbl_011_005", "(cont)", 4),
        notes="Four-part continuation stress case (rare worst case).",
    ))
    cases.append(CaseSpec(
        case_id="exp_two_tables_diff_titles_a",
        axes={"table": "two_distinct_titles", "pages": 1},
        page=PageSpec(page_count=1),
        tables=(
            _table("3.1", "DC characteristics", "tbl_003_001", top=100, body_h=240, rows=6),
            _table("3.2", "AC characteristics", "tbl_003_002", top=420, body_h=240, rows=6),
        ),
        notes="Two different tables with different titles on a single page.",
    ))
    cases.append(CaseSpec(
        case_id="exp_two_tables_diff_titles_b",
        axes={"table": "two_distinct_titles", "pages": 1},
        page=PageSpec(page_count=1),
        tables=(
            _table("13.1", "Clock source options", "tbl_013_001", top=100, body_h=240, rows=5),
            _table("13.2", "PLL configuration ranges", "tbl_013_002", top=420, body_h=240, rows=5),
        ),
        notes="Second representative of two distinct-titled tables on one page.",
    ))
    cases.append(CaseSpec(
        case_id="exp_wide_table_caption_above_b",
        axes={"table": "single_page_wide", "width": "wide"},
        page=PageSpec(page_count=1),
        tables=(_table("14.3", "Wide register field map", "tbl_014_003", x0=36, x1=576, top=120, body_h=320, rows=8, cols=8),),
        notes="Second wide table representative with caption above body.",
    ))
    cases.append(CaseSpec(
        case_id="exp_table_same_page_fragment",
        axes={"table": "same_page_fragment"},
        page=PageSpec(page_count=1),
        tables=(
            _table("15.2", "Bus arbitration order", "tbl_015_002", top=100, body_h=250, part=1, rows=6),
            _table("15.2", "Bus arbitration order", "tbl_015_002", top=420, body_h=250, part=2, cont=True, marker="(cont)", page=1, cont_from="tbl_015_002", rows=6),
        ),
        notes="A table whose continuation fragment falls on the same page.",
        coverage_hints=("tbl.fragment:same_page_fragment",),
    ))

    # --- D7: common-region realism (structural diversity + deterministic jitter) ---
    cases.append(CaseSpec(
        case_id="exp_hf_header_rule_topright_subtitle",
        axes={"header": "rule_topright_subtitle", "pages": 2},
        page=PageSpec(page_count=2),
        header=HeaderFooterSpec(True, band(360, 18, 564, 54), HEADER_TEMPLATES["subtitle_only"], True, False, True),
        notes="Header with a rule and a top-right subsection subtitle (no page number).",
        coverage_hints=("hf.subtitle_position:top_right",),
    ))
    cases.append(CaseSpec(
        case_id="exp_hf_footer_rule_bottomright_page",
        axes={"footer": "rule_bottomright_page_x_of_y", "pages": 3},
        page=PageSpec(page_count=3),
        footer=HeaderFooterSpec(True, band(360, 740, 564, 774), FOOTER_TEMPLATES["page_x_of_y"], True, False, True),
        notes="Footer with a rule and a bottom-right 'Page x of y' counter.",
    ))
    cases.append(CaseSpec(
        case_id="exp_hf_multipart_footer_center_notice",
        axes={"footer": "multipart_left_center_right", "pages": 2},
        page=PageSpec(page_count=2),
        footer=HeaderFooterSpec(True, band(48, 740, 220, 774), HEADER_TEMPLATES["doc_title"], False, False, False),
        extra_regions=(
            HeaderFooterSpec(True, band(225, 740, 470, 774), FOOTER_TEMPLATES["distribution_notice"], False, False, False, kind="footer"),
            HeaderFooterSpec(True, band(500, 740, 564, 774), FOOTER_TEMPLATES["page_only"], True, False, False, kind="footer"),
        ),
        notes="Multi-part footer: left document title, center distribution notice, right page number.",
        coverage_hints=("hf.page_number_position:bottom_right",),
    ))
    cases.append(CaseSpec(
        case_id="exp_hf_first_page_suppressed",
        axes={"header": "first_page_suppressed", "pages": 3},
        page=PageSpec(page_count=3),
        header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["subtitle_page"], True, False, False, first_page_suppressed=True),
        notes="Running header suppressed on the first page, present on pages 2+.",
    ))
    cases.append(CaseSpec(
        case_id="exp_hf_evenodd_mirror_with_jitter",
        axes={"header": "evenodd_mirror_jitter", "pages": 4},
        page=PageSpec(page_count=4),
        header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["subtitle_page"], True, mirrored_even_odd=True, rule_line=True, jitter_x=3, jitter_y=2),
        notes="Even/odd mirrored header with small deterministic per-page x/y jitter.",
    ))
    cases.append(CaseSpec(
        case_id="exp_hf_rule_y_jitter",
        axes={"header_footer": "both_rules_rule_jitter", "pages": 3},
        page=PageSpec(page_count=3),
        header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["plain"], False, rule_line=True, rule_jitter_y=2),
        footer=HeaderFooterSpec(True, band(48, 740, 564, 774), FOOTER_TEMPLATES["plain"], False, rule_line=True, rule_jitter_y=2),
        notes="Header and footer rules whose y position jitters slightly per page.",
    ))
    cases.append(CaseSpec(
        case_id="exp_wm_license_text_position_jitter",
        axes={"watermark": "variable_license_position_jitter", "pages": 3},
        page=PageSpec(page_count=3),
        watermark=WatermarkSpec(True, band(120, 310, 500, 510), WATERMARK_TEMPLATES["licensed"], True, 0, 0.13, "center", jitter_pos=4),
        notes="Variable per-page license watermark with deterministic position jitter.",
    ))
    cases.append(CaseSpec(
        case_id="exp_wm_near_footer_rotation_opacity_jitter",
        axes={"watermark": "near_footer_rot_opacity_jitter", "pages": 3},
        page=PageSpec(page_count=3),
        watermark=WatermarkSpec(True, band(120, 690, 500, 740), WATERMARK_TEMPLATES["confidential"], False, 8, 0.18, "center", jitter_rot=4, jitter_opacity=0.05, near_footer=True),
        notes="Watermark sitting just above the footer band, with per-page rotation/opacity jitter.",
    ))

    return cases


def _seq_header_two_line() -> HeaderFooterSpec:
    return HeaderFooterSpec(True, band(48, 18, 564, 58), HEADER_TEMPLATES["two_line"], True, rule_line=True)


def _seq_footer_bar_two_line() -> HeaderFooterSpec:
    return HeaderFooterSpec(True, band(48, 726, 564, 770), FOOTER_TEMPLATES["bar_two_line"], True, rule_line=True)


def d9_sequence_cases() -> List[CaseSpec]:
    """D9 step2: curated figure/table sequence + title/gap + header-combined cases.

    Bodies/captions are stacked by SequenceBuilder so the layout_sequence order
    matches actual y-order, and interstitial 1/2-line text is recorded as
    non-target with metadata. Bodies kept modest so two targets fit one page.
    """
    cases: List[CaseSpec] = []

    # --- 10 required sequence cases ----------------------------------------
    sb = SequenceBuilder()
    sb.figure("3-3", "Reset sequence timing", body_kind="waveform", body_h=150).figure("3-4", "Clock distribution path", body_kind="diagram", body_h=150)
    cases.append(sb.build_case("exp_seq_fig_fig", {"sequence": "figure_figure"},
                               notes="Two figures stacked with no interstitial text."))

    sb = SequenceBuilder()
    sb.figure("3-5", "Sampled output", body_kind="waveform", body_h=140).text(1).figure("3-6", "PLL lock detail", body_kind="diagram", body_h=140)
    cases.append(sb.build_case("exp_seq_fig_t1_fig", {"sequence": "figure_text1_figure"},
                               notes="Figure, one-line interstitial text, figure."))

    sb = SequenceBuilder()
    sb.figure("4-1", "Power domains", body_kind="diagram", body_h=140).text(2).figure("4-2", "Sequenced enables", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_seq_fig_t2_fig", {"sequence": "figure_text2_figure"},
                               notes="Figure, two-line interstitial text, figure."))

    sb = SequenceBuilder()
    sb.figure("5-1", "Bus topology", body_kind="diagram", body_h=150).table("5-1", "Bus signal map", "tbl_seq_5_1", body_h=150)
    cases.append(sb.build_case("exp_seq_fig_table", {"sequence": "figure_table"},
                               notes="Figure directly followed by a table."))

    sb = SequenceBuilder()
    sb.table("6-1", "Register summary", "tbl_seq_6_1", body_h=160).figure("6-1", "Register access timing", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_seq_table_fig", {"sequence": "table_figure"},
                               notes="Table directly followed by a figure."))

    sb = SequenceBuilder()
    sb.table("7-1", "DC characteristics", "tbl_seq_7_1", body_h=150).table("7-2", "AC characteristics", "tbl_seq_7_2", body_h=150)
    cases.append(sb.build_case("exp_seq_table_table", {"sequence": "table_table"},
                               notes="Two tables stacked with no interstitial text."))

    sb = SequenceBuilder()
    sb.table("8-1", "Pin assignments", "tbl_seq_8_1", body_h=150).text(1).figure("8-1", "Pin timing", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_seq_table_t1_fig", {"sequence": "table_text1_figure"},
                               notes="Table, one-line interstitial text, figure."))

    sb = SequenceBuilder()
    sb.table("9-1", "Interrupt map", "tbl_seq_9_1", body_h=150).text(2).figure("9-1", "Interrupt latency", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_seq_table_t2_fig", {"sequence": "table_text2_figure"},
                               notes="Table, two-line interstitial text, figure."))

    sb = SequenceBuilder()
    sb.figure("10-1", "Memory layout", body_kind="diagram", body_h=140).text(1).table("10-1", "Memory regions", "tbl_seq_10_1", body_h=150)
    cases.append(sb.build_case("exp_seq_fig_t1_table", {"sequence": "figure_text1_table"},
                               notes="Figure, one-line interstitial text, table."))

    sb = SequenceBuilder()
    sb.figure("11-1", "DMA channels", body_kind="diagram", body_h=140).text(2).table("11-1", "DMA priorities", "tbl_seq_11_1", body_h=150)
    cases.append(sb.build_case("exp_seq_fig_t2_table", {"sequence": "figure_text2_table"},
                               notes="Figure, two-line interstitial text, table."))

    # --- title position / gap combinations (full figure&table x above/below x 0/1/2) ---
    def _one(case_id, axes_v, *, target, caption_pos, gap_lines):
        b = SequenceBuilder()
        if target == "figure":
            b.figure("12-1", "Datapath overview", body_kind="diagram", caption_pos=caption_pos, gap_lines=gap_lines, body_h=220)
        else:
            b.table("13-1", "Timing parameters", "tbl_gap_13_1", caption_pos=caption_pos, gap_lines=gap_lines, body_h=230)
        return b.build_case(case_id, {"title_gap": axes_v},
                            notes=f"{target} title {caption_pos}, gap {gap_lines} line(s).")

    cases.append(_one("exp_gap_fig_above_g0", "fig_above_g0", target="figure", caption_pos="above", gap_lines=0))
    cases.append(_one("exp_gap_fig_above_g1", "fig_above_g1", target="figure", caption_pos="above", gap_lines=1))
    cases.append(_one("exp_gap_fig_above_g2", "fig_above_g2", target="figure", caption_pos="above", gap_lines=2))
    cases.append(_one("exp_gap_fig_below_g0", "fig_below_g0", target="figure", caption_pos="below", gap_lines=0))
    cases.append(_one("exp_gap_fig_below_g2", "fig_below_g2", target="figure", caption_pos="below", gap_lines=2))
    cases.append(_one("exp_gap_tbl_above_g0", "tbl_above_g0", target="table", caption_pos="above", gap_lines=0))
    cases.append(_one("exp_gap_tbl_above_g2", "tbl_above_g2", target="table", caption_pos="above", gap_lines=2))
    cases.append(_one("exp_gap_tbl_below_g0", "tbl_below_g0", target="table", caption_pos="below", gap_lines=0))
    cases.append(_one("exp_gap_tbl_below_g1", "tbl_below_g1", target="table", caption_pos="below", gap_lines=1))
    cases.append(_one("exp_gap_tbl_below_g2", "tbl_below_g2", target="table", caption_pos="below", gap_lines=2))

    # --- header/footer combined sequence cases -----------------------------
    sb = SequenceBuilder()
    sb.figure("14-1", "Top-level block", body_kind="diagram", body_h=140).figure("14-2", "Subsystem detail", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_hfseq_2line_header_fig_fig", {"sequence": "figure_figure", "hf": "two_line_header"},
                               header=_seq_header_two_line(),
                               notes="Two-line running header above a figure-figure sequence."))

    sb = SequenceBuilder()
    sb.figure("15-1", "Interface diagram", body_kind="diagram", body_h=140).table("15-1", "Interface signals", "tbl_seq_15_1", body_h=150)
    cases.append(sb.build_case("exp_hfseq_footerbar_fig_table", {"sequence": "figure_table", "hf": "footer_bar_two_line"},
                               footer=_seq_footer_bar_two_line(),
                               notes="Figure-table sequence above a two-line ruled footer bar."))

    sb = SequenceBuilder()
    sb.table("16-1", "Mode table", "tbl_seq_16_1", body_h=150).text(1).figure("16-1", "Mode transition", body_kind="waveform", body_h=140)
    cases.append(sb.build_case("exp_hfseq_jitter_table_t1_fig", {"sequence": "table_text1_figure", "hf": "jitter"},
                               header=HeaderFooterSpec(True, band(48, 18, 564, 54), HEADER_TEMPLATES["subtitle_page"], True, rule_line=True, jitter_x=3, jitter_y=2),
                               footer=HeaderFooterSpec(True, band(48, 740, 564, 774), FOOTER_TEMPLATES["confidential_page"], True, rule_line=True, rule_jitter_y=2),
                               notes="Table-text-figure sequence with jittered header and footer."))

    return cases


def all_cases() -> List[CaseSpec]:
    return core_cases() + negative_cases() + expanded_cases() + d9_sequence_cases()
