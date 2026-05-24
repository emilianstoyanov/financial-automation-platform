"""Application service for LLM data extraction."""

from pathlib import Path
from app.tasks.llm.llm_extractor import LLMDataExtractor
from app.tasks.llm.models import ExtractedFinancialRecord, ExtractionBatchResult
from app.tasks.llm.constants import DEFAULT_COMPARISON_REPORT, DEFAULT_OUTPUT_JSON


class LLMApplicationService:
    """Facade for ``LLMDataExtractor`` used by API handlers."""

    def __init__(
            self,
            output_json: str | Path = DEFAULT_OUTPUT_JSON,
            comparison_report: str | Path = DEFAULT_COMPARISON_REPORT,
    ) -> None:
        self._extractor = LLMDataExtractor(
            output_json=output_json,
            comparison_report=comparison_report,
        )

    def process_sample_documents(self, persist: bool = True) -> ExtractionBatchResult:
        """Process all assignment sample documents."""
        return self._extractor.process_sample_documents(persist=persist)

    def extract_from_text(
            self,
            text: str,
            source_document: str = "inline.txt",
            persist: bool = False,
            model: str | None = None,
    ) -> ExtractedFinancialRecord:
        """Extract structured data from arbitrary document text."""
        return self._extractor.extract_from_document(
            text,
            source_document=source_document,
            model=model,
        )
