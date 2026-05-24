"""ETL pipeline service for financial CSV processing."""

import json
import pandas as pd
from pathlib import Path
from app.core.data_dirs import ensure_data_directories
from app.core.logging_config import get_logger
from app.tasks.etl.constants import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_QUALITY_REPORT,
    FX_RATES_TO_BGN,
)
from app.tasks.etl.exceptions import ETLError, ETLFileNotFoundError, ETLProcessingError
from app.tasks.etl.models import CleanFinancialRecord, ETLResult, QualityReport, RejectedRow
from app.tasks.etl.transformers import (
    convert_to_bgn,
    is_missing,
    normalize_category,
    normalize_currency,
    parse_date,
    parse_numeric,
    record_fingerprint,
)

logger = get_logger(__name__)


class ETLPipelineService:
    """Extract, clean, and load financial rows from a CSV into JSON and a quality report."""

    def __init__(
            self,
            input_path: str | Path = DEFAULT_INPUT_FILE,
            output_json_path: str | Path = DEFAULT_OUTPUT_JSON,
            report_path: str | Path = DEFAULT_QUALITY_REPORT,
    ) -> None:
        """Set input CSV path and output locations (defaults under ``data/etl/``)."""
        self.input_path = Path(input_path)
        self.output_json_path = Path(output_json_path)
        self.report_path = Path(report_path)

    def run(self, persist: bool = True) -> ETLResult:
        """Run extract → transform → dedupe; optionally persist outputs to disk."""
        if not self.input_path.is_file():
            raise ETLFileNotFoundError(f"Input file not found: {self.input_path}")

        try:
            ensure_data_directories()
            logger.info("Starting ETL pipeline for %s", self.input_path)
            raw_df = self._extract()
            report = QualityReport(total_rows=len(raw_df))

            candidates, report, rejected_rows = self._transform(raw_df, report)
            cleaned_records, report, rejected_rows = self._deduplicate(
                candidates, report, rejected_rows
            )

            report.cleaned_rows = len(cleaned_records)
            report.removed_rows = report.total_rows - report.cleaned_rows

            if persist:
                self._load(cleaned_records, report)

            logger.info(
                "ETL completed: %s cleaned, %s removed",
                report.cleaned_rows,
                report.removed_rows,
            )
            return ETLResult(
                status="success",
                report=report,
                records=cleaned_records,
                rejected_rows=rejected_rows,
            )

        except ETLError:
            raise
        except Exception as exc:
            logger.exception("ETL pipeline failed")
            raise ETLProcessingError("ETL pipeline failed") from exc

    def _extract(self) -> pd.DataFrame:
        """Read ``input_path`` as string-typed CSV; require all financial columns."""
        try:
            df = pd.read_csv(self.input_path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError as exc:
            raise ETLProcessingError("Input CSV is empty") from exc
        except Exception as exc:
            raise ETLProcessingError(f"Failed to read CSV: {self.input_path}") from exc

        required_columns = {"date", "company_id", "revenue", "expenses", "currency", "category"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ETLProcessingError(f"CSV missing required columns: {sorted(missing)}")

        return df

    def _transform(
            self, df: pd.DataFrame, report: QualityReport
    ) -> tuple[list[tuple[CleanFinancialRecord, int, dict[str, str]]], QualityReport, list[RejectedRow]]:
        """Validate each row and increment ``report`` counters for rejected rows."""
        candidates: list[tuple[CleanFinancialRecord, int, dict[str, str]]] = []
        rejected_rows: list[RejectedRow] = []

        for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
            original_data = self._original_row_data(row)
            record, reason = self._process_row(row)
            if reason is not None:
                self._increment_report_counter(report, reason)
                rejected_rows.append(
                    RejectedRow(
                        row_number=row_number,
                        reason=reason,
                        original_data=original_data,
                    )
                )
                continue
            if record is not None:
                candidates.append((record, row_number, original_data))

        return candidates, report, rejected_rows

    @staticmethod
    def _original_row_data(row: dict) -> dict[str, str]:
        return {key: "" if value is None else str(value) for key, value in row.items()}

    @staticmethod
    def _increment_report_counter(report: QualityReport, reason: str) -> None:
        if reason.startswith("invalid_date"):
            report.invalid_date_rows += 1
        elif reason.startswith("invalid_numeric"):
            report.invalid_numeric_rows += 1
        elif reason.startswith("duplicate_row"):
            report.duplicate_rows_removed += 1
        elif reason.startswith("missing_value") or reason.startswith("invalid_currency"):
            report.missing_value_rows += 1

    def _process_row(self, row: dict) -> tuple[CleanFinancialRecord | None, str | None]:
        """Return a BGN record, or ``(None, reason)`` when the row is rejected."""
        company_id = str(row.get("company_id", "")).strip()
        if is_missing(company_id):
            return None, "missing_value: company_id is empty"

        parsed_date = parse_date(row.get("date"))
        if parsed_date is None:
            return None, "invalid_date: date is missing or unparseable"

        revenue_raw = row.get("revenue")
        expenses_raw = row.get("expenses")

        if is_missing(revenue_raw):
            return None, "missing_value: revenue is empty"
        if is_missing(expenses_raw):
            return None, "missing_value: expenses is empty"

        revenue = parse_numeric(revenue_raw)
        expenses = parse_numeric(expenses_raw)

        if revenue is None:
            return None, "invalid_numeric_value: revenue is not a number"
        if expenses is None:
            return None, "invalid_numeric_value: expenses is not a number"

        currency = normalize_currency(row.get("currency"))
        if currency is None:
            return None, "invalid_currency: unsupported or missing currency"

        profit = round(revenue - expenses, 2)
        revenue_bgn = convert_to_bgn(revenue, currency)
        expenses_bgn = convert_to_bgn(expenses, currency)
        profit_bgn = round(revenue_bgn - expenses_bgn, 2)

        return (
            CleanFinancialRecord(
                date=parsed_date,
                company_id=company_id,
                revenue=revenue_bgn,
                expenses=expenses_bgn,
                profit=profit_bgn,
                currency="BGN",
                original_currency=currency,
                category=normalize_category(row.get("category")),
            ),
            None,
        )

    def _deduplicate(
            self,
            candidates: list[tuple[CleanFinancialRecord, int, dict[str, str]]],
            report: QualityReport,
            rejected_rows: list[RejectedRow],
    ) -> tuple[list[CleanFinancialRecord], QualityReport, list[RejectedRow]]:
        """Keep first occurrence per fingerprint; count extras as duplicates removed."""
        seen: set[tuple] = set()
        unique: list[CleanFinancialRecord] = []

        for record, row_number, original_data in candidates:
            key = record_fingerprint(
                record.date,
                record.company_id,
                record.revenue,
                record.expenses,
                record.original_currency,
                record.category,
            )
            if key in seen:
                report.duplicate_rows_removed += 1
                rejected_rows.append(
                    RejectedRow(
                        row_number=row_number,
                        reason="duplicate_row: identical record already kept",
                        original_data=original_data,
                    )
                )
                continue
            seen.add(key)
            unique.append(record)

        return unique, report, rejected_rows

    def _load(self, records: list[CleanFinancialRecord], report: QualityReport) -> None:
        """Write cleaned JSON to ``output_json_path`` and text report to ``report_path``."""
        self.output_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "metadata": {
                "source_file": str(self.input_path),
                "record_count": len(records),
                "fx_rates_to_bgn": FX_RATES_TO_BGN,
            },
            "records": [record.to_dict() for record in records],
        }

        with self.output_json_path.open("w", encoding="utf-8") as json_file:
            json.dump(payload, json_file, indent=2, ensure_ascii=False)

        with self.report_path.open("w", encoding="utf-8") as report_file:
            report_file.write(report.format_text())

        logger.info("Wrote cleaned data to %s", self.output_json_path)
        logger.info("Wrote quality report to %s", self.report_path)
