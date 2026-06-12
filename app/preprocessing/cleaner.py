"""Text cleaning and light metadata extraction for parsed documents."""

import re

from app.ingestion.base import ParsedDocument, ParsedPage

_MULTISPACE = re.compile(r"[ \t\u00a0]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
# Lines that are just page numbers like "12" or "Page 12 of 30".
_PAGE_NUMBER_LINE = re.compile(r"^\s*(page\s+)?\d+(\s+of\s+\d+)?\s*$", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Normalize whitespace and strip obvious header/footer page-number noise."""
    lines = []
    for line in text.splitlines():
        if _PAGE_NUMBER_LINE.match(line):
            continue
        line = _MULTISPACE.sub(" ", line).strip()
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = _MULTINEWLINE.sub("\n\n", cleaned)
    return cleaned.strip()


def clean_document(doc: ParsedDocument) -> ParsedDocument:
    """Return a copy of the document with each page's text cleaned."""
    cleaned_pages = [
        ParsedPage(page_number=p.page_number, text=clean_text(p.text))
        for p in doc.pages
    ]
    # Drop pages that became empty after cleaning.
    cleaned_pages = [p for p in cleaned_pages if p.text]
    metadata = {k: v for k, v in doc.metadata.items() if v}
    return ParsedDocument(
        filename=doc.filename,
        content_type=doc.content_type,
        pages=cleaned_pages,
        metadata=metadata,
    )
