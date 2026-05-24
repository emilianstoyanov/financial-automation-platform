"""Domain models for LLM extraction results."""

from typing import Any
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field


@dataclass
class ExtractedFinancialRecord:
    """Unified structured record extracted from a financial document."""

    company_name: str | None
    document_date: str | None
    total_amount: float | None
    currency: str | None
    expense_or_income_category: str | None
    financial_metrics: dict[str, Any]
    source_document: str
    extraction_method: str
    validation_errors: list[str] = field(default_factory=list)
    original_amount_text: str | None = None
    original_unit: str | None = None
    normalized_amount: float | None = None
    normalization_note: str | None = None
    primary_currency: str | None = None
    detected_currencies: list[str] = field(default_factory=list)
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionBatchResult:
    """Outcome of processing one or more documents."""

    status: str
    extraction_method: str
    documents: list[ExtractedFinancialRecord] = field(default_factory=list)
    traditional_documents: list[ExtractedFinancialRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    model: str | None = None

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def preview(self) -> list[dict[str, Any]]:
        return [doc.to_dict() for doc in self.documents[:10]]

    def to_json_payload(self) -> dict[str, Any]:
        return {
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "total_documents": self.total_documents,
                "extraction_method": self.extraction_method,
                "model": self.model,
                "status": self.status,
            },
            "documents": [doc.to_dict() for doc in self.documents],
            "errors": self.errors,
        }
