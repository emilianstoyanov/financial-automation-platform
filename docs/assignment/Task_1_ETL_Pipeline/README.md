# Task 1: ETL Pipeline with Python

## Description
You are provided with a CSV file containing financial data that has various data quality issues.

## Your Task
Create a Python script that:

1. **Extract**
   - Load data from `dirty_financial_data.csv`

2. **Transform**
   - Clean invalid records
   - Standardize date formats
   - Handle missing values
   - Remove duplicate records
   - Validate numeric fields (revenue, expenses)
   - Add calculated field `profit` (revenue - expenses)
   - Convert all amounts to BGN (use fixed rates: EUR=1.96, USD=1.80, GBP=2.30)

3. **Load**
   - Save cleaned data in JSON format
   - Generate a data quality report (how many records removed, why, etc.)

4. **Additional Requirements**
   - Implement error handling
   - Add logging
   - Create unit tests for core functions

## Expected Files
- `etl_pipeline.py` - main script
- `output_clean_data.json` - cleaned data
- `data_quality_report.txt` - quality report
- `tests.py` - unit tests

## Evaluation Criteria
- Correctness of data processing
- Code quality and structure
- Error handling and logging
- Documentation (comments, docstrings)
