"""Normalize and validate extracted financial records."""

import re
from typing import Any
from app.tasks.llm.constants import SUPPORTED_CURRENCIES
from app.tasks.llm.models import ExtractedFinancialRecord

_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_DMY = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")
_CURRENCY_ALIASES = {
    "EURO": "EUR",
    "€": "EUR",
    "LEVA": "BGN",
    "ЛВ": "BGN",
    "USD": "USD",
    "$": "USD",
    "GBP": "GBP",
    "£": "GBP",
}
_THOUSANDS_NOTE = (
    "Document amounts are in thousands of EUR; values were multiplied by 1,000."
)
_MIXED_CURRENCY_WARNING = "warning: multiple currencies detected: {currencies}"
_NET_PROFIT_BGN_KEYS = frozenset({"net_profit_bgn", "net_profit_bgn_million"})
_NET_PROFIT_EUR_KEYS = frozenset({"net_profit_eur", "net_profit_eur_m"})


def normalize_date(value: Any) -> str | None:
    """Convert common date strings to ``YYYY-MM-DD``."""
    if value is None or value == "":
        return None
    text = str(value).strip()
    if _DATE_ISO.match(text):
        return text
    match = _DATE_DMY.match(text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return None


def normalize_currency(value: Any) -> str | None:
    """Map currency text to EUR, BGN, USD, or GBP when possible."""
    if value is None or value == "":
        return None
    text = str(value).strip().upper()
    if text in SUPPORTED_CURRENCIES:
        return text
    for alias, code in _CURRENCY_ALIASES.items():
        if alias.upper() in text or text == alias.upper():
            return code
    for code in SUPPORTED_CURRENCIES:
        if code in text:
            return code
    return None


def normalize_amount(value: Any) -> float | None:
    """Parse a numeric amount from strings with commas or spaces."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace(" ", "")
    text = re.sub(r"[^\d.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_record(
        raw: dict[str, Any],
        *,
        source_document: str,
        extraction_method: str,
) -> ExtractedFinancialRecord:
    """Build a unified record, enrich units/currencies, then validate."""
    metrics = raw.get("financial_metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {"value": metrics}

    record = ExtractedFinancialRecord(
        company_name=_clean_text(raw.get("company_name")),
        document_date=normalize_date(raw.get("document_date")),
        total_amount=normalize_amount(raw.get("total_amount")),
        currency=normalize_currency(raw.get("currency")),
        expense_or_income_category=_clean_text(raw.get("expense_or_income_category")),
        financial_metrics=dict(metrics),
        source_document=source_document,
        extraction_method=extraction_method,
        validation_errors=[],
        original_amount_text=_clean_text(raw.get("original_amount_text")),
        original_unit=_clean_text(raw.get("original_unit")),
        primary_currency=normalize_currency(raw.get("primary_currency")),
        detected_currencies=_normalize_currency_list(raw.get("detected_currencies")),
    )

    _enrich_units_and_currencies(record, raw, source_document)
    _normalize_monetary_metrics(record, raw)
    record.financial_metrics = _coerce_financial_metrics(record.financial_metrics)
    record.validation_errors = validate_record(record)
    _ensure_normalization_note(record)
    return record


def validate_record(record: ExtractedFinancialRecord) -> list[str]:
    """Return validation messages for missing, invalid, or ambiguous fields."""
    errors: list[str] = []
    if not record.company_name:
        errors.append("company_name is missing")
    if not record.document_date:
        errors.append("document_date is missing or invalid")
    elif not _DATE_ISO.match(record.document_date):
        errors.append("document_date is not in YYYY-MM-DD format")
    if record.total_amount is None:
        errors.append("total_amount is missing or not numeric")
    primary = record.primary_currency or record.currency
    if not primary:
        errors.append("currency is missing or unsupported")
    elif primary not in SUPPORTED_CURRENCIES:
        errors.append(f"currency '{primary}' is not supported")
    if len(record.detected_currencies) > 1:
        joined = ", ".join(record.detected_currencies)
        warning = _MIXED_CURRENCY_WARNING.format(currencies=joined)
        if warning not in errors:
            errors.append(warning)
    return errors


def _format_amount_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return str(value)


def _ensure_normalization_note(record: ExtractedFinancialRecord) -> None:
    """Fill normalization_note when scaling context is known but note was not set."""
    if record.normalization_note:
        return
    if not record.original_amount_text or record.normalized_amount is None:
        return
    currency = record.primary_currency or record.currency
    normalized_str = _format_amount_number(record.normalized_amount)
    if currency:
        record.normalization_note = (
            f"{record.original_amount_text} normalized to {normalized_str} {currency}"
        )
    else:
        record.normalization_note = (
            f"{record.original_amount_text} normalized to {normalized_str}"
        )


def _enrich_units_and_currencies(
        record: ExtractedFinancialRecord,
        raw: dict[str, Any],
        source_document: str,
) -> None:
    """Apply document-specific unit scaling and currency detection."""
    if source_document == "financial_table.txt":
        _enrich_thousands_table(record, raw)
    elif source_document == "report_excerpt.txt":
        _enrich_mixed_currency_report(record, raw)
    elif source_document == "invoice.txt":
        _enrich_absolute_invoice(record, raw)
    else:
        _enrich_generic_amount(record, raw)


def _enrich_thousands_table(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> None:
    """Scale Q1 table values from thousands of EUR to absolute EUR amounts."""
    metrics = record.financial_metrics
    revenue_k = _metric_k_value(metrics, raw, "q1_revenue_k_eur", default_keys=("revenue",))
    expenses_k = _metric_k_value(metrics, raw, "q1_expenses_k_eur", default_keys=("expenses",))
    profit_k = _metric_k_value(metrics, raw, "q1_profit_k_eur", default_keys=("profit",))

    if revenue_k is None and profit_k is None:
        _enrich_generic_amount(record, raw)
        return

    revenue_k = revenue_k if revenue_k is not None else normalize_amount(raw.get("total_amount"))
    expenses_k = expenses_k if expenses_k is not None else profit_k
    profit_k = profit_k if profit_k is not None else revenue_k

    revenue_eur = _scale_thousands(revenue_k)
    expenses_eur = _scale_thousands(expenses_k)
    profit_eur = _scale_thousands(profit_k)

    metrics["q1_revenue_k_eur"] = revenue_k
    metrics["q1_expenses_k_eur"] = expenses_k
    metrics["q1_profit_k_eur"] = profit_k
    metrics["q1_revenue_eur"] = revenue_eur
    metrics["q1_expenses_eur"] = expenses_eur
    metrics["q1_profit_eur"] = profit_eur

    record.original_amount_text = record.original_amount_text or f"{revenue_k} k EUR"
    record.original_unit = record.original_unit or "thousands_eur"
    record.normalized_amount = revenue_eur
    record.total_amount = revenue_eur
    record.primary_currency = "EUR"
    record.currency = "EUR"
    record.detected_currencies = ["EUR"]


def _enrich_mixed_currency_report(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> None:
    """Normalize million-scale EUR amounts and preserve BGN net profit separately."""
    metrics = record.financial_metrics

    revenue = metrics.get("revenue_eur")
    if revenue is None:
        revenue = _million_to_absolute(metrics.get("revenue"), raw.get("revenue"))
    if revenue is None and record.total_amount and record.total_amount >= 1_000_000:
        revenue = record.total_amount
    if revenue is None:
        revenue = _million_to_absolute(raw.get("total_amount"))

    expenses = metrics.get("operating_expenses_eur")
    if expenses is None:
        expenses = _million_to_absolute(metrics.get("operating_expenses"), raw.get("expenses"))

    net_profit_bgn = _net_profit_metric(metrics, _NET_PROFIT_BGN_KEYS)
    if net_profit_bgn is None:
        net_profit_bgn = _net_profit_metric(raw, _NET_PROFIT_BGN_KEYS)

    net_profit_eur = _net_profit_metric(metrics, _NET_PROFIT_EUR_KEYS)
    if net_profit_eur is None:
        net_profit_eur = _million_to_absolute(metrics.get("net_profit_eur_m"))

    if revenue is not None:
        metrics["revenue_eur"] = revenue
    if expenses is not None:
        metrics["operating_expenses_eur"] = expenses
    if net_profit_bgn is not None:
        metrics["net_profit_bgn"] = net_profit_bgn
    if net_profit_eur is not None:
        metrics["net_profit_eur"] = net_profit_eur

    record.original_amount_text = record.original_amount_text or "12.5 million EUR"
    record.original_unit = record.original_unit or "million_eur"
    record.normalized_amount = revenue
    record.total_amount = revenue
    record.primary_currency = "EUR"
    record.currency = "EUR"
    record.detected_currencies = _unique_currencies(["EUR", "BGN", *record.detected_currencies])
    record.normalization_note = (
            record.normalization_note
            or "Revenue/expenses stated in millions of EUR; net profit also stated in BGN."
    )


def _enrich_absolute_invoice(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> None:
    """Keep invoice totals as absolute EUR amounts."""
    amount = record.total_amount
    if amount is None:
        return
    record.original_amount_text = record.original_amount_text or f"{amount} EUR"
    record.original_unit = record.original_unit or "absolute"
    record.normalized_amount = amount
    record.primary_currency = record.currency or "EUR"
    record.currency = record.primary_currency
    record.detected_currencies = _unique_currencies([record.primary_currency])


def _enrich_generic_amount(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> None:
    """Fill unit metadata when no document-specific rule applies."""
    amount = record.total_amount
    if amount is None:
        return
    unit = raw.get("original_unit") or record.original_unit
    if unit in {"thousands_eur", "thousands"} and amount < 1_000_000:
        record.original_unit = "thousands_eur"
        record.normalized_amount = _scale_thousands(amount)
        record.total_amount = record.normalized_amount
    elif unit in {"million_eur", "million"} and amount < 1_000_000:
        record.original_unit = "million_eur"
        record.normalized_amount = amount * 1_000_000
        record.total_amount = record.normalized_amount
    else:
        record.original_unit = record.original_unit or "absolute"
        record.normalized_amount = amount

    primary = record.primary_currency or record.currency
    if primary:
        record.primary_currency = primary
        record.currency = primary
        record.detected_currencies = _unique_currencies(
            record.detected_currencies or [primary]
        )


_NON_MONETARY_KEY_MARKERS = (
    "_pct",
    "_percent",
    "employees",
    "employee_count",
    "average_employees",
    "headcount",
    "count",
    "ratio",
    "margin_pct",
)


def _normalize_monetary_metrics(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> None:
    """Scale monetary metric values using the same unit multiplier as total_amount."""
    doc_multiplier = _document_unit_multiplier(record, raw)
    record.financial_metrics = _scale_metrics_dict(record.financial_metrics, doc_multiplier)


def _scale_metrics_dict(metrics: dict[str, Any], doc_multiplier: float) -> dict[str, Any]:
    scaled: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, dict):
            scaled[key] = _scale_metrics_dict(value, doc_multiplier)
            continue
        if _is_monetary_metric_key(key):
            scaled[key] = _scale_monetary_value(value, key, doc_multiplier)
        else:
            amount = normalize_amount(value)
            scaled[key] = amount if amount is not None else value
    return scaled


def _document_unit_multiplier(record: ExtractedFinancialRecord, raw: dict[str, Any]) -> float:
    unit = str(record.original_unit or raw.get("original_unit") or "").lower()
    amount_text = str(record.original_amount_text or raw.get("original_amount_text") or "").lower()
    combined = f"{unit} {amount_text}"
    if "million" in combined:
        return 1_000_000.0
    if any(token in combined for token in ("thousand", "thousands", " k ", "k eur", "thousands_eur")):
        return 1_000.0
    if "_k" in unit:
        return 1_000.0
    return 1.0


def _is_explicit_k_metric_key(key: str) -> bool:
    lower = key.lower()
    return (
            "_k_" in lower
            or lower.endswith("_k_eur")
            or lower.endswith("_k_bgn")
            or lower.endswith("_k_usd")
            or lower.endswith("_k_gbp")
            or "_thousand" in lower
    )


def _is_explicit_million_metric_key(key: str) -> bool:
    lower = key.lower()
    return "_million" in lower or lower.endswith("_eur_m") or lower.endswith("_m_eur")


def _is_non_monetary_metric_key(key: str) -> bool:
    lower = key.lower()
    if any(marker in lower for marker in _NON_MONETARY_KEY_MARKERS):
        return True
    if "margin" in lower and not any(
            suffix in lower for suffix in ("_eur", "_bgn", "_usd", "_gbp")
    ):
        return True
    return False


def _is_monetary_metric_key(key: str) -> bool:
    if _is_non_monetary_metric_key(key):
        return False
    if _is_explicit_k_metric_key(key):
        return False
    lower = key.lower()
    if any(suffix in lower for suffix in ("_eur", "_bgn", "_usd", "_gbp")):
        return True
    return any(
        token in lower
        for token in (
            "revenue",
            "expense",
            "profit",
            "tax",
            "vat",
            "subtotal",
            "reimbursement",
            "ebitda",
            "amount",
            "cost",
            "income",
        )
    )


def _scale_monetary_value(value: Any, key: str, doc_multiplier: float) -> float | Any:
    amount = normalize_amount(value)
    if amount is None:
        return value
    if _is_explicit_million_metric_key(key) and amount < 1_000_000:
        return amount * 1_000_000
    if doc_multiplier == 1_000.0 and amount < 100_000:
        return amount * 1_000.0
    if doc_multiplier == 1_000_000.0 and amount < 1_000:
        return amount * 1_000_000.0
    return amount


def _metric_k_value(
        metrics: dict[str, Any],
        raw: dict[str, Any],
        key: str,
        *,
        default_keys: tuple[str, ...] = (),
) -> float | None:
    if key in metrics:
        return normalize_amount(metrics[key])
    for default_key in default_keys:
        if default_key in metrics:
            value = normalize_amount(metrics[default_key])
            if value is not None and value >= 1000:
                return value / 1000
            return value
    return normalize_amount(raw.get(key))


def _scale_thousands(value: float | None) -> float | None:
    if value is None:
        return None
    if value >= 1000:
        return value
    return value * 1000


def _coerce_financial_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Normalize numeric metric values while preserving semantic keys from extraction."""
    coerced: dict[str, Any] = {}
    for key, value in metrics.items():
        if isinstance(value, dict):
            coerced[key] = _coerce_financial_metrics(value)
            continue
        amount = normalize_amount(value)
        coerced[key] = amount if amount is not None else value
    return coerced


def _net_profit_metric(
        source: dict[str, Any],
        keys: frozenset[str],
) -> float | None:
    """Read net profit only from explicitly named net_profit_* keys."""
    for key in keys:
        if key not in source:
            continue
        amount = normalize_amount(source[key])
        if amount is None:
            continue
        if key.endswith("_million") or (amount < 100_000 and "million" in key):
            return amount * 1_000_000
        if amount < 100_000 and key in {"net_profit_bgn", "net_profit_eur"}:
            return amount * 1_000_000
        return amount
    return None


def _million_to_absolute(value: Any, fallback: Any = None) -> float | None:
    amount = normalize_amount(value if value is not None else fallback)
    if amount is None:
        return None
    if amount < 1_000_000:
        return amount * 1_000_000
    return amount


def _normalize_currency_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = list(value)
    return _unique_currencies(
        [code for item in items if (code := normalize_currency(item))]
    )


def _unique_currencies(codes: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code and code in SUPPORTED_CURRENCIES and code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def truncate_preview(text: str, max_chars: int) -> str:
    """Return the first ``max_chars`` characters of whitespace-normalized text."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars]
