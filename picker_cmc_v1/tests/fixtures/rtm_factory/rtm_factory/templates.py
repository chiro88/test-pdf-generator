from __future__ import annotations

HEADER_TEMPLATES = {
    "chapter_page": "Chapter {chapter} · Page {page}",
    "subtitle_page": "{subtitle} · {page}",
    "plain": "Technical Reference Manual",
}

FOOTER_TEMPLATES = {
    "confidential_page": "Confidential — {page}",
    "doc_rev_page": "Rev A · {page}",
    "plain": "Internal Use Only",
}

WATERMARK_TEMPLATES = {
    "draft": "DRAFT",
    "licensed": "Licensed to {user}",
    "confidential": "CONFIDENTIAL",
}

FIGURE_CAPTION_TEMPLATES = {
    "Figure": "Figure {index}. {title}",
    "Fig.": "Fig. {index}. {title}",
    "FIGURE": "FIGURE {index}. {title}",
}

TABLE_CAPTION_TEMPLATES = {
    "normal": "Table {index}. {title}",
    "continued": "Table {index}. {title} {suffix}",
}

SUBTITLES = [
    "Clocking Overview",
    "Register Interface",
    "Timing Characteristics",
    "Power Sequencing",
]

USERS = [
    "alpha@example.test",
    "beta@example.test",
    "gamma@example.test",
]


def render_template(template: str, *, page: int, page_offset: int = 0, chapter: int = 2, subtitle: str = "Overview", user: str = "user@example.test") -> str:
    return template.format(
        page=page + page_offset,
        chapter=chapter,
        subtitle=subtitle,
        user=user,
    )
