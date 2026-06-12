"""Core data types shared across the ingestion pipeline."""

from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    """A single page/section of a parsed source document."""

    page_number: int
    text: str


@dataclass
class ParsedDocument:
    """Normalized output of any parser, regardless of source file type."""

    filename: str
    content_type: str
    pages: list[ParsedPage]
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)
