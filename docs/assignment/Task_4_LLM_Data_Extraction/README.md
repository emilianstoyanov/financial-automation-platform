# Task 4: LLM-assisted Data Extraction

## Description
Use an LLM (Large Language Model) to extract structured data from unstructured financial documents.

## Context
In the `sample_documents/` folder you'll find 3 differently formatted documents with financial information:
- `invoice.txt` - invoice in free text
- `financial_table.txt` - semi-structured table
- `report_excerpt.txt` - excerpt from financial report

## Your Task

1. **LLM Integration**
   - Use Anthropic Claude API or OpenAI API
   - API keys: You can use environment variable or config file
   - For testing purposes, you may use mock responses

2. **Data Extraction**
   For each document extract:
   - Company name
   - Document date
   - Total amount
   - Currency
   - Expense/income category
   - Other relevant financial metrics

3. **Data Normalization**
   - Convert all extracted data into unified structure
   - Standardize date formats
   - Normalize currencies

4. **Validation**
   - Implement validation of LLM output
   - Validate that extracted amounts are numbers
   - Check that dates are in proper format
   - Mark missing or invalid data

5. **Comparison (bonus)**
   - Implement traditional approach (regex, string parsing)
   - Compare accuracy and reliability vs LLM approach
   - Document advantages and disadvantages

## Expected Files
- `llm_extractor.py` - main script
- `data_extractor.py` - extractor
- `extracted_data.json` - structured results
- `comparison_report.md` - comparative analysis
- `tests.py` - unit tests

## Example Structure
```python
class LLMDataExtractor:
    def __init__(self, api_key=None, model='claude-sonnet-4.5'):
        ...
    
    def extract_from_document(self, document_text):
        ...
    
    def normalize_data(self, raw_extraction):
        ...
    
    def validate_extraction(self, data):
        ...
```

## Evaluation Criteria
- Proper LLM API integration
- Quality of prompt engineering
- Robust validation logic
- Edge case handling
- Comparative analysis (if done)
