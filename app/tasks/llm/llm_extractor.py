"""LLM-assisted financial data extraction with OpenAI or deterministic mock fallback."""

from __future__ import annotations

import json
import logging
from typing import Any
from pathlib import Path
from app.core.config import get_settings
from app.core.data_dirs import ensure_data_directories
from app.tasks.llm.comparison import generate_comparison_report
from app.tasks.llm.constants import (
    DEFAULT_COMPARISON_REPORT,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_LLM_LOG,
    SAMPLE_DOCUMENT_NAMES,
    SAMPLE_DOCUMENTS_DIR,
)
from app.tasks.llm.data_extractor import TraditionalDataExtractor
from app.tasks.llm.exceptions import LLMAPIError, LLMDocumentNotFoundError
from app.tasks.llm.logging_setup import setup_llm_logging
from app.tasks.llm.models import ExtractedFinancialRecord, ExtractionBatchResult
from app.tasks.llm.normalizer import normalize_record

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """Extract financial data from the document below.
Return ONLY valid JSON-like fields with exactly these keys:
- company_name (string)
- document_date (string, prefer YYYY-MM-DD)
- total_amount (number, use the numeric value as stated in the document — do not scale thousands/millions yourself)
- currency (string: EUR, BGN, USD, or GBP — primary currency for total_amount)
- primary_currency (string, when document has a main reporting currency)
- detected_currencies (array of ISO codes present in the document)
- original_amount_text (string, e.g. "848.0 k EUR" or "12.5 million EUR")
- original_unit (string: absolute, thousands_eur, or million_eur)
- expense_or_income_category (string)
- financial_metrics (object): one snake_case key per labeled amount in the document, named from the source text (e.g. tax_adjustment_bgn, vat_eur, reimbursement_eur, operating_expenses_eur, ebitda_margin_pct). Append _eur, _bgn, _usd, or _gbp when the currency is clear. Use net_profit_bgn / net_profit_eur only when the source explicitly says net profit. Do not rename tax, VAT, reimbursement, EBITDA, or other line items to net_profit (e.g. "Additional local tax adjustment: 42,300 BGN" -> tax_adjustment_bgn: 42300, not net_profit_bgn)

Document:
{text}
"""


class LLMDataExtractor:
    """Extract structured financial data via OpenAI or deterministic mock rules."""

    def __init__(
            self,
            api_key: str | None = None,
            model: str = DEFAULT_OPENAI_MODEL,
            output_json: str | Path = DEFAULT_OUTPUT_JSON,
            comparison_report: str | Path = DEFAULT_COMPARISON_REPORT,
            log_file: str = DEFAULT_LLM_LOG,
    ) -> None:
        """Configure API credentials, model, and output paths."""
        settings = get_settings()
        self._api_key = settings.openai_api_key if api_key is None else api_key
        self._model = model or settings.openai_model
        self._output_json = Path(output_json)
        self._comparison_report = Path(comparison_report)
        self._log_file = log_file
        self._traditional = TraditionalDataExtractor()

    @property
    def uses_openai(self) -> bool:
        """True when an OpenAI API key is configured."""
        return bool(self._api_key)

    def process_sample_documents(self, persist: bool = True) -> ExtractionBatchResult:
        """Extract data from all assignment sample documents and optionally persist outputs."""
        ensure_data_directories()
        setup_llm_logging(self._log_file)

        method = "openai" if self.uses_openai else "mock"
        logger.info("LLM extraction started: %s documents, method=%s", len(SAMPLE_DOCUMENT_NAMES), method)

        documents: list[ExtractedFinancialRecord] = []
        traditional_documents: list[ExtractedFinancialRecord] = []
        errors: list[str] = []

        for name in SAMPLE_DOCUMENT_NAMES:
            path = SAMPLE_DOCUMENTS_DIR / name
            if not path.is_file():
                message = f"Sample document not found: {path}"
                errors.append(message)
                logger.warning(message)
                continue

            text = path.read_text(encoding="utf-8")
            try:
                llm_record = self.extract_from_document(text, source_document=name)
                trad_record = self._traditional.extract_from_document(text, source_document=name)
                documents.append(llm_record)
                traditional_documents.append(trad_record)
                logger.info(
                    "Extracted %s — company=%s, amount=%s %s",
                    name,
                    llm_record.company_name,
                    llm_record.total_amount,
                    llm_record.currency,
                )
            except LLMAPIError as exc:
                errors.append(f"{name}: {exc}")
                logger.warning("Extraction failed for %s: %s", name, exc)

        status = "success" if documents and not errors else "partial" if documents else "failed"
        batch_model = self._resolved_model(None, method)
        result = ExtractionBatchResult(
            status=status,
            extraction_method=method,
            documents=documents,
            traditional_documents=traditional_documents,
            errors=errors,
            model=batch_model,
        )

        if persist:
            self._save_results(result)
            self._save_comparison_report(result)

        logger.info(
            "LLM extraction finished: %s document(s), %s error(s), status=%s",
            len(documents),
            len(errors),
            status,
        )
        return result

    def extract_from_document(
            self,
            document_text: str,
            source_document: str = "inline.txt",
            model: str | None = None,
    ) -> ExtractedFinancialRecord:
        """Extract, normalize, and validate one document."""
        if self.uses_openai:
            raw = self._extract_with_openai(document_text, model=model)
            method = "openai"
        else:
            raw = self._extract_with_mock(document_text, source_document)
            method = "mock"

        record = normalize_record(
            raw,
            source_document=source_document,
            extraction_method=method,
        )
        record.model = self._resolved_model(model, method)
        return record

    def _resolved_model(self, model: str | None, method: str) -> str:
        if method == "mock":
            return "mock"
        return model or self._model

    def normalize_data(self, raw_extraction: dict[str, Any]) -> ExtractedFinancialRecord:
        """Normalize a raw extraction dict (public helper for tests and pipelines)."""
        return normalize_record(
            raw_extraction,
            source_document=raw_extraction.get("source_document", "unknown"),
            extraction_method=raw_extraction.get("extraction_method", "mock"),
        )

    def validate_extraction(self, record: ExtractedFinancialRecord) -> list[str]:
        """Return validation errors for an extracted record."""
        return list(record.validation_errors)

    def _extract_with_openai(
            self,
            document_text: str,
            model: str | None = None,
    ) -> dict[str, Any]:
        """Call OpenAI chat completions and parse strict JSON output."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMAPIError("openai package is not installed") from exc

        prompt = _EXTRACTION_PROMPT.format(text=document_text)
        client = OpenAI(api_key=self._api_key)
        use_model = model or self._model

        try:
            response = client.chat.completions.create(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMAPIError("OpenAI response was not valid JSON") from exc
        except Exception as exc:
            raise LLMAPIError(f"OpenAI API call failed: {exc}") from exc

    def _extract_with_mock(self, document_text: str, source_document: str) -> dict[str, Any]:
        """Deterministic mock extraction for local testing without an API key."""
        if "TechnoSoft" in document_text or source_document == "invoice.txt":
            return {
                "company_name": "TechnoSoft Ltd",
                "document_date": "2024-03-15",
                "total_amount": 5916.60,
                "currency": "EUR",
                "original_amount_text": "5916.60 EUR",
                "original_unit": "absolute",
                "expense_or_income_category": "services",
                "financial_metrics": {
                    "subtotal_eur": 4930.50,
                    "vat_eur": 986.10,
                    "software_maintenance_eur": 2400.00,
                    "consulting_eur": 1850.00,
                    "cloud_infrastructure_eur": 680.50,
                },
            }

        if "BusinessGroup" in document_text or source_document == "financial_table.txt":
            return {
                "company_name": "BusinessGroup JSC",
                "document_date": "2024-04-05",
                "total_amount": 848.0,
                "currency": "EUR",
                "original_amount_text": "848.0 k EUR",
                "original_unit": "thousands_eur",
                "expense_or_income_category": "revenue",
                "financial_metrics": {
                    "q1_revenue_k_eur": 848.0,
                    "q1_expenses_k_eur": 612.9,
                    "q1_profit_k_eur": 235.1,
                    "january_profit_k_eur": 58.2,
                    "february_profit_k_eur": 88.2,
                    "march_profit_k_eur": 88.7,
                },
            }

        if "InvestCapital" in document_text or source_document == "report_excerpt.txt":
            return {
                "company_name": "InvestCapital LLC",
                "document_date": "2024-02-28",
                "total_amount": 12.5,
                "currency": "EUR",
                "primary_currency": "EUR",
                "detected_currencies": ["EUR", "BGN"],
                "original_amount_text": "12.5 million EUR",
                "original_unit": "million_eur",
                "expense_or_income_category": "income",
                "financial_metrics": {
                    "revenue_eur": 12_500_000,
                    "operating_expenses_eur": 8_300_000,
                    "net_profit_bgn": 3_200_000,
                    "net_profit_eur": 1_640_000,
                    "ebitda_margin_pct": 18.5,
                    "average_employees": 47,
                },
            }

        trad = self._traditional.extract_from_document(document_text, source_document)
        return {
            "company_name": trad.company_name,
            "document_date": trad.document_date,
            "total_amount": trad.total_amount,
            "currency": trad.currency,
            "expense_or_income_category": trad.expense_or_income_category,
            "financial_metrics": trad.financial_metrics,
        }

    def _save_results(self, result: ExtractionBatchResult) -> None:
        """Write ``data/llm/extracted_data.json``."""
        self._output_json.parent.mkdir(parents=True, exist_ok=True)
        with self._output_json.open("w", encoding="utf-8") as handle:
            json.dump(result.to_json_payload(), handle, indent=2, ensure_ascii=False)
        logger.info("Saved extraction results to %s", self._output_json)

    def _save_comparison_report(self, result: ExtractionBatchResult) -> None:
        """Write ``data/llm/comparison_report.md``."""
        report = generate_comparison_report(result.documents, result.traditional_documents)
        self._comparison_report.parent.mkdir(parents=True, exist_ok=True)
        self._comparison_report.write_text(report, encoding="utf-8")
        logger.info("Saved comparison report to %s", self._comparison_report)


def load_sample_document(name: str) -> str:
    """Read one assignment sample document by filename."""
    path = SAMPLE_DOCUMENTS_DIR / name
    if not path.is_file():
        raise LLMDocumentNotFoundError(f"Sample document not found: {path}")
    return path.read_text(encoding="utf-8")
