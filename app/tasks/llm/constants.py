"""Constants for LLM data extraction."""

from pathlib import Path
from typing import Final
from app.core.data_dirs import LLM_DATA_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DOCUMENTS_DIR: Final[Path] = (
        PROJECT_ROOT / "docs" / "assignment" / "Task_4_LLM_Data_Extraction" / "sample_documents"
)
DEFAULT_OUTPUT_JSON: Final[str] = str(LLM_DATA_DIR / "extracted_data.json")
DEFAULT_COMPARISON_REPORT: Final[str] = str(LLM_DATA_DIR / "comparison_report.md")
DEFAULT_LLM_LOG: Final[str] = "logs/llm.log"

SAMPLE_DOCUMENT_NAMES: Final[tuple[str, ...]] = (
    "invoice.txt",
    "financial_table.txt",
    "report_excerpt.txt",
)

SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset({"EUR", "BGN", "USD", "GBP"})
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-4o-mini"
DASHBOARD_OPENAI_MODELS: Final[tuple[str, ...]] = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4.1",
)

EXTRACTION_JSON_KEYS: Final[tuple[str, ...]] = (
    "company_name",
    "document_date",
    "total_amount",
    "currency",
    "expense_or_income_category",
    "financial_metrics",
)
