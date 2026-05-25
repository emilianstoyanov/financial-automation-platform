"""ETL domain models."""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RejectedRow:
    """One CSV row rejected during ETL with reason and original values."""

    row_number: int
    reason: str
    original_data: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "row_number": self.row_number,
            "reason": self.reason,
            "original_data": dict(self.original_data),
        }


@dataclass(frozen=True)
class CleanFinancialRecord:
    """Normalized financial record with amounts in BGN."""

    date: str
    company_id: str
    revenue: float
    expenses: float
    profit: float
    currency: str
    original_currency: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityReport:
    """Data quality metrics produced by the ETL pipeline."""

    total_rows: int = 0
    cleaned_rows: int = 0
    removed_rows: int = 0
    duplicate_rows_removed: int = 0
    invalid_numeric_rows: int = 0
    invalid_date_rows: int = 0
    missing_value_rows: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def format_text(self, rejected_rows: list[RejectedRow] | None = None) -> str:
        """Format counters and per-row rejection details for ``data_quality_report.txt``."""
        lines = [
            "Data Quality Report",
            "====================",
            f"Total rows:              {self.total_rows}",
            f"Cleaned rows:            {self.cleaned_rows}",
            f"Removed rows:            {self.removed_rows}",
            f"Duplicate rows removed:  {self.duplicate_rows_removed}",
            f"Invalid numeric rows:    {self.invalid_numeric_rows}",
            f"Invalid date rows:       {self.invalid_date_rows}",
            f"Missing value rows:      {self.missing_value_rows}",
        ]
        rows = rejected_rows or []
        lines.append("")
        lines.append("Rejected rows")
        lines.append("-------------")
        if not rows:
            lines.append("(none)")
        else:
            for entry in rows:
                lines.append(f"Row {entry.row_number}: {entry.reason}")
                for key, value in entry.original_data.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


@dataclass
class ETLResult:
    """Result of a completed ETL run."""

    status: str
    report: QualityReport
    records: list[CleanFinancialRecord] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)

    @property
    def preview(self) -> list[dict]:
        """First 10 cleaned records as dicts for API responses."""
        return [record.to_dict() for record in self.records[:10]]

    @property
    def rejected_rows_preview(self) -> list[dict]:
        """Rejected rows as dicts for API responses."""
        return [row.to_dict() for row in self.rejected_rows]
