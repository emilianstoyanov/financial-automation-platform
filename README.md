# Financial Automation Platform

A **FastAPI** backend that automates common financial data workflows: clean CSV data (ETL), fetch exchange rates, scrape public documents, and extract structured fields from unstructured text with an LLM (or local mock rules).

This README is written for someone **new to the repo** — no prior context required.

---

## Table of contents

1. [What is included](#what-is-included)
2. [First-time setup](#first-time-setup)
3. [Start the server](#start-the-server)
4. [Try it in the browser (Swagger)](#try-it-in-the-browser-swagger)
5. [Where output files are saved](#where-output-files-are-saved)
6. [API overview](#api-overview)
7. [Task 1 — ETL Pipeline](#task-1--etl-pipeline)
8. [Task 2 — Exchange Rates](#task-2--exchange-rates)
9. [Task 3 — Document Scraping](#task-3--document-scraping)
10. [Task 4 — LLM Data Extraction](#task-4--llm-data-extraction)
11. [Configuration](#configuration)
12. [Project structure](#project-structure)
13. [Run all tests](#run-all-tests)
14. [Deploy to Heroku](#deploy-to-heroku)
15. [Further reading](#further-reading)

---

## What is included

| Task | Purpose | Main output on disk |
|------|---------|---------------------|
| **1 — ETL** | Clean messy financial CSV (dates, numbers, duplicates) and convert amounts to BGN | `data/etl/output_clean_data.json`, `data/etl/data_quality_report.txt` |
| **2 — Exchange** | Live EUR / USD / GBP rates vs BGN (cached 1 hour) | `data/exchange/cache.json` |
| **3 — Scraping** | Find PDFs on web pages, download, extract metadata + text preview | `data/scraping/extracted_documents.json` |
| **4 — LLM** | Extract company, date, amounts, currencies, metrics from text | `data/llm/extracted_data.json`, `data/llm/comparison_report.md` |

Original assignment specs live under `docs/assignment/`.

---

## First-time setup

You need **Python 3.11+** and a terminal opened in the project root (`financial-automation-platform/`).

### Step 1 — Virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

**Optional (Task 3 only)** — headless browser fallback for sites that block plain HTTP:

```bash
playwright install chromium
```

### Step 3 — Environment file

Copy the example env file and edit if needed:

**Windows:**

```powershell
copy .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

| Variable | Required? | Notes |
|----------|-----------|--------|
| *(none for basic demo)* | | ETL, exchange, scraping (without browser), and LLM **mock** work out of the box |
| `OPENAI_API_KEY` | Optional | Task 4 live OpenAI extraction; without it, deterministic **mock** rules are used |
| `SCRAPING_BROWSER_FALLBACK=true` | Optional | Task 3 Playwright fallback after `requests` fails |
| `EXCHANGE_RATE_API_URL` | Optional | Default points to Exchangerate-API (no API key) |

> **Note:** Runtime files under `data/` and `logs/` are **not committed to git** (see `.gitignore`). After setup you only see empty folders with `.gitkeep` until you call the APIs below.

---

## Start the server

With the virtual environment active:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the app will:

- Create folder tree: `data/etl`, `data/exchange`, `data/scraping`, `data/llm`, `logs`
- Initialize SQLite at `data/financial_data.db`
- **Not** run ETL, scraping, or LLM jobs automatically — you trigger those via API

---

## Try it in the browser (Swagger)

1. Open **[http://localhost:8000/](http://localhost:8000/)** — local **dashboard** (ETL, exchange, scraping, LLM forms).
2. Or open **[http://localhost:8000/docs](http://localhost:8000/docs)** (Swagger UI).
3. Expand a section (**ETL**, **Exchange**, **Scraping**, **LLM**).
4. Click **Try it out** → **Execute**.
5. Read the JSON response; for tasks that persist files, check the paths in [Where output files are saved](#where-output-files-are-saved).

Quick health check:

```bash
curl http://localhost:8000/api/v1/health
```

Alternative API docs: **[http://localhost:8000/redoc](http://localhost:8000/redoc)**

---

## Where output files are saved

Understanding **when** files appear avoids confusion.

| Path | Created when | Not created when |
|------|----------------|------------------|
| `data/etl/output_clean_data.json` | `POST /api/v1/etl/process-local-file` or `POST /api/v1/etl/upload` | Server start only |
| `data/etl/data_quality_report.txt` | Same ETL endpoints | Server start only |
| `data/exchange/cache.json` | First `GET /api/v1/exchange/rates` or `convert` (then refreshed hourly) | Server start only |
| `data/scraping/extracted_documents.json` | Scraping endpoints (see Task 3) | Server start only |
| `data/llm/extracted_data.json` | `GET /api/v1/llm/process-sample-documents` | Server start; **`POST /llm/extract` does not write here** |
| `data/llm/comparison_report.md` | `GET /api/v1/llm/process-sample-documents` | Server start; **`POST /llm/extract` does not write here** |
| `logs/scraping.log` | Task 3 scraping runs | — |
| `logs/llm.log` | Task 4 batch run (`process-sample-documents`) | — |
| `logs/app.log` | General app logging (if configured) | — |

**Task 4 — important:** Pasting custom text in Swagger under `POST /api/v1/llm/extract` returns JSON in the **HTTP response only**. To save results to disk, use `GET /api/v1/llm/process-sample-documents` (processes the three assignment sample files).

---

## API overview

| Method | Endpoint | Writes files? |
|--------|----------|---------------|
| `GET` | `/` | No — local dashboard UI |
| `GET` | `/api/v1/health` | No |
| `POST` | `/api/v1/etl/process-local-file` | Yes — ETL outputs |
| `POST` | `/api/v1/etl/upload` | Yes — ETL outputs |
| `GET` | `/api/v1/exchange/rates` | Yes — cache |
| `GET` | `/api/v1/exchange/convert` | Yes — cache (on miss) |
| `GET` | `/api/v1/scraping/process-local-urls` | Yes — scraping JSON |
| `POST` | `/api/v1/scraping/scrape-url` | Yes — scraping JSON |
| `POST` | `/api/v1/scraping/scrape-html` | Yes — scraping JSON |
| `GET` | `/api/v1/llm/process-sample-documents` | Yes — LLM JSON + report |
| `POST` | `/api/v1/llm/extract` | **No** — response only |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

---

## Task 1 — ETL Pipeline

Cleans financial CSV data (dates, numbers, duplicates), converts amounts to BGN, and writes a JSON dataset plus a quality report.

### Input

| Item | Path |
|------|------|
| Default sample CSV | `data/etl/dirty_financial_data.csv` |
| Assignment copy | `docs/assignment/Task_1_ETL_Pipeline/dirty_financial_data.csv` |

**Required columns:** `date`, `company_id`, `revenue`, `expenses`, `currency`, `category`

### Run (Swagger or curl)

| Method | Endpoint | Use case |
|--------|----------|----------|
| `POST` | `/api/v1/etl/process-local-file` | Process the repo sample file |
| `POST` | `/api/v1/etl/upload` | Upload your own `.csv` (multipart form) |

```bash
curl -X POST http://localhost:8000/api/v1/etl/process-local-file
```

```bash
curl -X POST http://localhost:8000/api/v1/etl/upload -F "file=@path/to/your.csv"
```

Response includes `status`, `quality_report`, and `preview` (first 10 cleaned rows).

### Output

| File | Description |
|------|-------------|
| `data/etl/output_clean_data.json` | Cleaned records (amounts in BGN, `profit` calculated) |
| `data/etl/data_quality_report.txt` | Counts: removed rows, duplicates, invalid dates/numbers, etc. |

Fixed FX rates used in ETL: EUR **1.96** · USD **1.80** · GBP **2.30** · BGN **1.00**.

### Tests

```bash
pytest tests/tasks/test_etl_task1.py tests/api/test_etl.py
```

Spec: `docs/assignment/Task_1_ETL_Pipeline/README.md`

---

## Task 2 — Exchange Rates

Fetches live EUR / USD / GBP rates against BGN via [Exchangerate-API](https://www.exchangerate-api.com/) (no API key). Results are cached for **one hour** in `data/exchange/cache.json`.

### Examples

**Rates** (BGN per 1 unit of foreign currency):

```bash
curl http://localhost:8000/api/v1/exchange/rates
```

**Convert** — supported: `BGN`, `EUR`, `USD`, `GBP`:

```bash
curl "http://localhost:8000/api/v1/exchange/convert?from_currency=EUR&to_currency=BGN&amount=100"
```

Or use the **Exchange** section in [Swagger](http://localhost:8000/docs).

### Tests

```bash
pytest tests/tasks/test_exchange_client.py tests/api/test_exchange.py
```

Spec: `docs/assignment/Task_2_API_Integration/README.md`

---

## Task 3 — Document Scraping

Discovers PDF links on public pages (up to 20 per page), downloads files, extracts metadata and a **500-character** text preview, and appends results to JSON. Failed URLs are logged without stopping the whole batch.

### Files

| Item | Path |
|------|------|
| URL list | `data/scraping/sample_urls.txt` |
| Offline HTML fixture (demo) | `data/scraping/fixtures/minfin_bg_1394_demo.html` |
| Output | `data/scraping/extracted_documents.json` |
| Log | `logs/scraping.log` |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/scraping/process-local-urls` | Scrape all URLs from `sample_urls.txt` |
| `POST` | `/api/v1/scraping/scrape-url` | Scrape one page URL |
| `POST` | `/api/v1/scraping/scrape-html` | Scrape from browser-saved HTML (e.g. after Cloudflare) |

```bash
curl http://localhost:8000/api/v1/scraping/process-local-urls
```

```bash
curl -X POST http://localhost:8000/api/v1/scraping/scrape-url \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://www.nsi.bg/pages/informacionna-sistema-biznes-cikli-97\"}"
```

### Cloudflare / blocked sites

Some hosts (e.g. `www.minfin.bg`) return **403** to simple bots. The scraper records the error in JSON and `logs/scraping.log` without crashing.

**Options:**

1. **`POST /scrape-html`** — save the page HTML in the browser, paste or upload content.
2. **Offline URL** in `sample_urls.txt` — e.g. `offline:data/scraping/fixtures/minfin_bg_1394_demo.html`
3. **Playwright fallback** — in `.env` set `SCRAPING_BROWSER_FALLBACK=true` and run `playwright install chromium`. Uses headless Chromium with `bg-BG` locale after `requests` fails. Does **not** bypass CAPTCHAs or WAF challenges.

### Tests

```bash
pytest tests/tasks/test_scraping_parsers.py tests/tasks/test_scraping_scraper.py \
  tests/tasks/test_scraping_task3.py tests/tasks/test_scraping_page_fetcher.py \
  tests/tasks/test_scraping_cloudflare.py tests/api/test_scraping.py
```

Spec: `docs/assignment/Task_3_Document_Scraping/README.md`

---

## Task 4 — LLM Data Extraction

Extracts structured financial fields from unstructured text:

- `company_name`, `document_date`, `total_amount`, `currency`, `expense_or_income_category`
- `financial_metrics` (document-specific numbers)
- Unit metadata: `original_amount_text`, `original_unit`, `normalized_amount`, `normalization_note`
- Mixed currencies: `primary_currency`, `detected_currencies` (with a **non-fatal** validation warning when multiple currencies appear)

**Extraction engine:**

| Mode | When | `extraction_method` in output |
|------|------|-------------------------------|
| **OpenAI** | `OPENAI_API_KEY` set in `.env` | `openai` |
| **Mock** | No API key | `mock` (deterministic rules for sample documents) |

A **traditional regex** extractor always runs in parallel for the sample batch; differences are summarized in `comparison_report.md`.

### Sample input (assignment)

| File | Content hint |
|------|----------------|
| `docs/assignment/Task_4_LLM_Data_Extraction/sample_documents/invoice.txt` | Absolute EUR invoice |
| `.../financial_table.txt` | Amounts in **thousands of EUR** (normalized ×1,000) |
| `.../report_excerpt.txt` | **Mixed EUR + BGN** (revenue in EUR, net profit in BGN) |

### Endpoints

**Batch — writes files** (`data/llm/extracted_data.json`, `data/llm/comparison_report.md`, `logs/llm.log`):

```bash
curl http://localhost:8000/api/v1/llm/process-sample-documents
```

**Ad-hoc text — response only, no file write:**

```bash
curl -X POST http://localhost:8000/api/v1/llm/extract \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Company: TechnoSoft Ltd\\nDate: 15.03.2024\\nTOTAL AMOUNT DUE: 5916.60 EUR\"}"
```

In Swagger: **LLM** → `POST /api/v1/llm/extract` → paste text in the `text` field → **Execute**. Result appears in the response body only.

### Output files (after batch endpoint)

| File | Description |
|------|-------------|
| `data/llm/extracted_data.json` | All sample documents + metadata (`extraction_method`, validation, normalization fields) |
| `data/llm/comparison_report.md` | LLM/mock vs traditional regex; notes on unit scaling and mixed currencies |
| `logs/llm.log` | Processing log |

### Normalization examples (batch)

| Document | Raw unit | Normalized `total_amount` (EUR) |
|----------|----------|----------------------------------|
| `financial_table.txt` | thousands (`848.0 k`) | `848000` |
| `report_excerpt.txt` | millions (revenue) | `12500000` (+ `net_profit_bgn` kept separately in metrics) |

### Tests

```bash
pytest tests/tasks/test_llm_normalizer.py tests/tasks/test_llm_extractor.py tests/api/test_llm.py
```

Spec: `docs/assignment/Task_4_LLM_Data_Extraction/README.md`

---

## Configuration

Settings load from `.env` (see `.env.example`). Main variables:

| Variable | Default | Task |
|----------|---------|------|
| `DATABASE_URL` | `sqlite:///./data/financial_data.db` | App |
| `ENVIRONMENT` | `development` | App |
| `LOG_LEVEL` | `INFO` | App |
| `OPENAPI_ENABLED` | `true` | Docs at `/docs` |
| `EXCHANGE_RATE_API_URL` | Exchangerate-API BGN endpoint | 2 |
| `SCRAPING_BROWSER_FALLBACK` | `false` | 3 |
| `OPENAI_API_KEY` | *(unset)* | 4 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 4 |

---

## Project structure

```
app/
  api/v1/           # HTTP routes (etl, exchange, scraping, llm, health)
  core/             # Config, database, logging, data directory setup
  schemas/          # Pydantic request/response models
  services/         # Thin facades over task modules
  tasks/
    etl/            # Task 1 pipeline
    exchange/       # Task 2 API client + cache
    scraping/       # Task 3 scraper, PDF extract, parsers
    llm/            # Task 4 extractors, normalizer, comparison
  main.py           # FastAPI app factory
tests/              # Pytest (mirrors tasks + api)
data/               # Runtime outputs (gitignored except .gitkeep)
  etl/
  exchange/
  scraping/
  llm/
docs/
  assignment/       # Original task descriptions + sample inputs
  ARCHITECTURE.md   # High-level design notes
logs/               # Task and app logs (gitignored)
```

---

## Run all tests

```bash
pytest
```

Expected: full suite green (ETL, exchange, scraping, LLM, API).

---

## Deploy to Heroku

```bash
heroku create your-app-name
heroku config:set ENVIRONMENT=production DEBUG=false
git push heroku main
```

Uses `Procfile` (Gunicorn + Uvicorn workers) and `runtime.txt` (Python 3.11).

For production, consider PostgreSQL (`DATABASE_URL`) instead of SQLite.

---

## Further reading

| Document | Content |
|----------|---------|
| `docs/ARCHITECTURE.md` | Layers, data folders, extension points |
| `docs/assignment/GENERAL_INSTRUCTIONS.md` | Assignment overview |
| `docs/assignment/Task_*` | Per-task requirements |

---

## License

Internal / personal project.
