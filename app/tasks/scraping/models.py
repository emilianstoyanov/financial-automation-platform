"""Document scraping domain models."""

from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field


@dataclass
class ScrapedDocument:
    """Metadata and text preview for one PDF document."""

    title: str
    url: str
    size_kb: float | None
    date_published: str | None
    document_type: str
    content_preview: str
    scraped_at: str
    source_page: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScrapingResult:
    """Outcome of a scraping run."""

    status: str
    documents: list[ScrapedDocument] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def preview(self) -> list[dict]:
        return [doc.to_dict() for doc in self.documents[:10]]

    def to_json_payload(self) -> dict:
        return {
            "metadata": {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total_documents": self.total_documents,
            },
            "documents": [doc.to_dict() for doc in self.documents],
            "errors": self.errors,
        }
