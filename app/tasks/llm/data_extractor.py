"""Traditional regex/string-based financial data extraction."""

import re
from typing import Any
from app.tasks.llm.normalizer import normalize_record
from app.tasks.llm.models import ExtractedFinancialRecord

_COMPANY_PATTERN = re.compile(r"Company:\s*(.+)", re.IGNORECASE)
_DATE_PATTERN = re.compile(
    r"(?:Date|Report date|approved[^.\n]*on)\s*:?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
    re.IGNORECASE,
)
_TOTAL_INVOICE = re.compile(
    r"TOTAL\s+AMOUNT\s+DUE:\s*([\d,.\s]+)\s*([A-Z]{3})",
    re.IGNORECASE,
)
_TOTAL_Q1 = re.compile(
    r"TOTAL\s+Q1\s*\|\s*([\d,.\s]+)\s*\|\s*([\d,.\s]+)\s*\|\s*([\d,.\s]+)",
    re.IGNORECASE,
)
_MILLION_AMOUNT = re.compile(
    r"([\d,.\s]+)\s*million\s+([A-Z]{3})",
    re.IGNORECASE,
)
_TABLE_ROW = re.compile(
    r"^\|\s*(January|February|March|TOTAL Q1)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)


class TraditionalDataExtractor:
    """Extract financial fields using regex and string parsing only."""

    def extract_from_document(
            self,
            document_text: str,
            source_document: str = "unknown",
    ) -> ExtractedFinancialRecord:
        """Parse ``document_text`` and return a normalized, validated record."""
        raw = self._parse_document(document_text)
        return normalize_record(
            raw,
            source_document=source_document,
            extraction_method="traditional",
        )

    def _parse_document(self, text: str) -> dict[str, Any]:
        """Apply regex rules to pull structured fields from free text."""
        company = _COMPANY_PATTERN.search(text)
        date_match = _DATE_PATTERN.search(text)
        metrics: dict[str, Any] = {}

        raw: dict[str, Any] = {
            "company_name": company.group(1).strip() if company else None,
            "document_date": date_match.group(1) if date_match else None,
            "total_amount": None,
            "currency": None,
            "expense_or_income_category": None,
            "financial_metrics": metrics,
        }

        if "INVOICE" in text.upper():
            raw.update(self._parse_invoice(text))
        elif "|" in text and "Revenue" in text:
            raw.update(self._parse_financial_table(text, metrics))
        elif "Annual Financial Report" in text or "revenue reached" in text.lower():
            raw.update(self._parse_report_excerpt(text, metrics))

        return raw

    def _parse_invoice(self, text: str) -> dict[str, Any]:
        """Extract invoice totals and service category."""
        total = _TOTAL_INVOICE.search(text)
        if not total:
            return {"expense_or_income_category": "services"}
        return {
            "total_amount": total.group(1).replace(" ", ""),
            "currency": total.group(2),
            "original_amount_text": f"{total.group(1).strip()} {total.group(2)}",
            "original_unit": "absolute",
            "expense_or_income_category": "services",
            "financial_metrics": {
                "subtotal_eur": self._find_labeled_amount(text, r"Subtotal:\s*([\d,.\s]+)"),
                "vat_eur": self._find_labeled_amount(text, r"VAT.*?([\d,.\s]+)\s*EUR"),
            },
        }

    def _parse_financial_table(
            self, text: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract quarterly table rows and Q1 totals (amounts in thousands EUR)."""
        for row in _TABLE_ROW.finditer(text):
            month, revenue, expenses, profit = row.groups()
            key = month.strip().lower().replace(" ", "_")
            metrics[key] = {
                "revenue_k_eur": float(revenue),
                "expenses_k_eur": float(expenses),
                "profit_k_eur": float(profit),
            }

        total = _TOTAL_Q1.search(text)
        result: dict[str, Any] = {
            "currency": "EUR",
            "expense_or_income_category": "revenue",
            "financial_metrics": metrics,
            "original_unit": "thousands_eur",
            "detected_currencies": ["EUR"],
        }
        if total:
            result["total_amount"] = total.group(1)
            result["original_amount_text"] = f"{total.group(1).strip()} k EUR (Q1 profit)"
            metrics["q1_revenue_k_eur"] = float(total.group(1).strip())
            metrics["q1_expenses_k_eur"] = float(total.group(2).strip())
            metrics["q1_profit_k_eur"] = float(total.group(3).strip())
            result["original_amount_text"] = f"{total.group(1).strip()} k EUR (Q1 revenue)"
            result["total_amount"] = float(total.group(1).strip())
        return result

    def _parse_report_excerpt(
            self, text: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract revenue, expenses, and net profit from report prose."""
        amounts = list(_MILLION_AMOUNT.finditer(text))
        if amounts:
            metrics["revenue_eur"] = normalize_amount_from_match(amounts[0])
            if len(amounts) > 1:
                metrics["operating_expenses_eur"] = normalize_amount_from_match(amounts[1])

        net_profit = re.search(
            r"Net profit.*?([\d,.\s]+)\s*million\s+([A-Z]{3})",
            text,
            re.IGNORECASE,
        )
        net_profit_eur_match = re.search(
            r"EUR\s+([\d.]+)M",
            text,
            re.IGNORECASE,
        )
        ebitda = re.search(r"EBITDA margin:\s*([\d.]+)%", text, re.IGNORECASE)
        employees = re.search(r"employees:\s*(\d+)", text, re.IGNORECASE)
        if ebitda:
            metrics["ebitda_margin_pct"] = float(ebitda.group(1))
        if employees:
            metrics["average_employees"] = int(employees.group(1))

        result: dict[str, Any] = {
            "expense_or_income_category": "income",
            "financial_metrics": metrics,
            "detected_currencies": ["EUR", "BGN"],
            "original_unit": "million_eur",
        }
        if amounts:
            result["total_amount"] = amounts[0].group(1).replace(",", "").strip()
            result["original_amount_text"] = f"{amounts[0].group(1).strip()} million EUR"
            result["currency"] = amounts[0].group(2)
            result["primary_currency"] = amounts[0].group(2)
        if net_profit:
            metrics["net_profit_bgn"] = normalize_amount_from_match(net_profit)
            metrics["net_profit_bgn_currency"] = net_profit.group(2)
        if net_profit_eur_match:
            metrics["net_profit_eur"] = float(net_profit_eur_match.group(1).replace(",", "")) * 1_000_000
        return result

    @staticmethod
    def _find_labeled_amount(text: str, pattern: str) -> float | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", "").replace(" ", ""))
        except ValueError:
            return None


def normalize_amount_from_match(match: re.Match[str]) -> float:
    """Convert ``X million CUR`` regex match to absolute amount."""
    return float(match.group(1).replace(",", "").strip()) * 1_000_000
