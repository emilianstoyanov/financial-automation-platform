"""Generate comparison report between LLM/mock and traditional extraction."""

from app.tasks.llm.models import ExtractedFinancialRecord

_COMPARE_FIELDS = (
    "company_name",
    "document_date",
    "total_amount",
    "currency",
    "expense_or_income_category",
)


def generate_comparison_report(
        llm_records: list[ExtractedFinancialRecord],
        traditional_records: list[ExtractedFinancialRecord],
) -> str:
    """Build a short markdown report comparing both extraction approaches."""
    lines = [
        "# LLM vs Traditional Extraction Comparison",
        "",
        "Side-by-side field comparison for the sample financial documents.",
        "",
    ]

    trad_by_source = {r.source_document: r for r in traditional_records}
    for llm_doc in llm_records:
        trad = trad_by_source.get(llm_doc.source_document)
        lines.extend(_compare_document(llm_doc, trad))

    lines.extend(
        [
            "## Summary",
            "",
            "| Approach | Strengths | Weaknesses |",
            "|----------|-----------|------------|",
            "| LLM / mock | Handles varied prose and semi-structured text; flexible field mapping | Needs API key (or mock rules); output must be validated |",
            "| Traditional (regex) | Deterministic, fast, no external dependency | Fragile on format changes; misses context in free text |",
            "",
            "Recommendation: use traditional parsing for fixed templates; use LLM (with validation) for heterogeneous documents.",
            "",
            "Note: `total_amount` / `currency` mismatches are often due to unit normalization (thousands/millions) or mixed EUR/BGN documents — check `normalization_note` and `detected_currencies` in JSON output.",
        ]
    )
    return "\n".join(lines) + "\n"


def _compare_document(
        llm_doc: ExtractedFinancialRecord,
        trad_doc: ExtractedFinancialRecord | None,
) -> list[str]:
    lines = [
        f"## {llm_doc.source_document}",
        "",
        f"- LLM/mock method: `{llm_doc.extraction_method}`",
        f"- Traditional validation errors: {len(trad_doc.validation_errors) if trad_doc else 'n/a'}",
        f"- LLM/mock validation errors: {len(llm_doc.validation_errors)}",
        "",
        "| Field | LLM/mock | Traditional | Match |",
        "|-------|----------|-------------|-------|",
    ]
    mismatches: list[str] = []
    for field in _COMPARE_FIELDS:
        llm_val = getattr(llm_doc, field)
        trad_val = getattr(trad_doc, field) if trad_doc else None
        match = "yes" if llm_val == trad_val else "no"
        lines.append(f"| {field} | {llm_val} | {trad_val} | {match} |")
        if match == "no":
            mismatches.append(field)

    if mismatches:
        lines.append("")
        lines.append(_mismatch_note(llm_doc, trad_doc, mismatches))

    lines.append("")
    return lines


def _mismatch_note(
        llm_doc: ExtractedFinancialRecord,
        trad_doc: ExtractedFinancialRecord | None,
        fields: list[str],
) -> str:
    notes: list[str] = []
    if "total_amount" in fields:
        if llm_doc.original_unit in {"thousands_eur", "million_eur"} or (
                trad_doc and trad_doc.original_unit in {"thousands_eur", "million_eur"}
        ):
            notes.append(
                "total_amount differs because one side used raw table units (k EUR / millions) "
                f"and the other used normalized EUR (LLM unit={llm_doc.original_unit}, "
                f"traditional unit={getattr(trad_doc, 'original_unit', None)})."
            )
    if "currency" in fields:
        llm_currencies = llm_doc.detected_currencies or ([llm_doc.currency] if llm_doc.currency else [])
        trad_currencies = (
                trad_doc.detected_currencies or ([trad_doc.currency] if trad_doc and trad_doc.currency else [])
        )
        if len(set(llm_currencies + trad_currencies)) > 1:
            notes.append(
                "currency differs because the report contains mixed currencies "
                f"(LLM detected={llm_currencies}, traditional detected={trad_currencies}); "
                "primary total may use EUR revenue while net profit is also stated in BGN."
            )
    if not notes:
        notes.append("Fields differ due to category wording or extraction strategy, not missing data.")
    return "- **Mismatch note:** " + " ".join(notes)
