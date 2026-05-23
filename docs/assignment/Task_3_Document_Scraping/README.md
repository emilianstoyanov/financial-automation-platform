# Task 3: Document Scraping

## Description
Create a script to extract documents and metadata from web portals.

## Your Task
Write a Python script that:

1. **Web Scraping**
   - Scrapes the provided URLs (see `sample_urls.txt`)
   - Extracts 3-5 PDF links from the pages
   - Adds reasonable delay between requests

2. **Metadata Extraction**
   For each document found, collect:
   - Title/filename
   - URL
   - Size (if available)
   - Publication date (if available from HTML)
   - Document type

3. **Content Extraction**
   - Download PDF files (3-5)
   - Extract text content from PDFs
   - Save first 500 characters as preview

4. **Data Storage**
   - Structure data in JSON format
   - Or save to SQLite database

5. **Best Practices**
   - User-Agent header
   - Respectful scraping (delays, rate limiting)
   - Error handling for invalid URLs, missing pages
   - Process logging

## Sample URLs
The `sample_urls.txt` file contains test pages. You can add other publicly accessible Bulgarian company/institution websites.

## Expected Files
- `scraper.py` - main scraping script
- `extracted_documents.json` - resulting metadata
- `logs/scraping.log` - log file
- `tests.py` - unit tests

## Example Data Structure
```json
{
  "documents": [
    {
      "title": "Annual Report 2024",
      "url": "https://example.com/report.pdf",
      "size_kb": 1024,
      "date_published": "2024-03-15",
      "content_preview": "First 500 characters...",
      "scraped_at": "2024-10-17T10:30:00"
    }
  ]
}
```

## Evaluation Criteria
- Robust scraping logic
- Proper metadata extraction
- Ethical scraping practices
- Error handling
- Code quality
