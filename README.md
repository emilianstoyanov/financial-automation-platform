# Financial Automation Platform

FastAPI backend for financial data workflows: CSV ETL, live exchange rates, document scraping, and LLM (or mock) field extraction.

**Contents**

- [Live Demo](#live-demo)
- [What is included](#what-is-included)
- [Run locally](#run-locally)
- [API overview](#api-overview)
- [Tasks](#task-1--etl-pipeline)
- [Tests](#tests)
- [Deployment](#deployment)
- [Project structure](#project-structure)

---

## Live Demo

Production is deployed on **Heroku** and is ready to test in the browser.

No local setup or API keys are required for the live demo. The production environment is already configured for the available demo features, including LLM extraction.

| Resource | URL |
|----------|-----|
| App / dashboard | https://www.financial-automation-platform.xyz/ |
| Swagger | https://www.financial-automation-platform.xyz/docs |
| ReDoc | https://www.financial-automation-platform.xyz/redoc |
| Health check | https://www.financial-automation-platform.xyz/api/v1/health |

---

## What is included

| Task | Purpose | Main output |
|------|---------|-------------|
| **1 — ETL** | Clean financial CSV; convert to BGN | `data/etl/output_clean_data.json`, `data/etl/data_quality_report.txt` |
| **2 — Exchange** | EUR / USD / GBP vs BGN (1h cache) | `data/exchange/cache.json` |
| **3 — Scraping** | PDF discovery, download, metadata + text preview | `data/scraping/extracted_documents.json` |
| **4 — LLM** | Structured fields from unstructured text | `data/llm/extracted_data.json`, `data/llm/comparison_report.md` |

Assignment specs: `docs/assignment/`.

---

## Run locally

**Requirements:** Python 3.11+

```bash
git clone https://github.com/emilianstoyanov/financial-automation-platform.git
cd financial-automation-platform
python -m venv .venv
```

**Activate venv**

| OS | Command |
|----|---------|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Linux / macOS | `source .venv/bin/activate` |

```bash
pip install -r requirements.txt
```

**Environment** — copy `.env.example` to `.env`:

| OS | Command |
|----|---------|
| Windows | `copy .env.example .env` |
| Linux / macOS | `cp .env.example .env` |

| Variable | Required? | Notes |
|----------|-----------|--------|
| *(none for basic demo)* | | ETL, exchange, scraping, and LLM **mock mode** work without keys locally |
| `OPENAI_API_KEY` | Optional | Task 4 live OpenAI; otherwise deterministic **mock** |
| `SCRAPING_BROWSER_FALLBACK` | Optional | Task 3 Playwright after `requests` fails (`playwright install chromium`) |
| `EXCHANGE_RATE_API_URL` | Optional | Default: Exchangerate-API (no key) |

**Start server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Startup creates `data/*`, `logs/`, and SQLite at `data/financial_data.db`. Tasks run only via API — not on boot.

### Open the app

| Environment | Dashboard | Swagger | ReDoc |
|-------------|-----------|---------|-------|
| **Production** | https://www.financial-automation-platform.xyz/ | `/docs` | `/redoc` |
| **Local** | http://localhost:8000/ | http://localhost:8000/docs | http://localhost:8000/redoc |

Health: `curl http://localhost:8000/api/v1/health` (production: `/api/v1/health` on the host above).

> `data/` and `logs/` are gitignored; folders exist with `.gitkeep` until APIs run.

---

## API overview

| Method | Endpoint | Writes files? |
|--------|----------|---------------|
| `GET` | `/` | No — dashboard |
| `GET` | `/api/v1/health` | No |
| `POST` | `/api/v1/etl/process-local-file` | Yes |
| `POST` | `/api/v1/etl/upload` | Yes |
| `GET` | `/api/v1/exchange/rates` | Yes — cache |
| `GET` | `/api/v1/exchange/convert` | Yes — cache on miss |
| `GET` | `/api/v1/scraping/process-local-urls` | Yes |
| `POST` | `/api/v1/scraping/scrape-url` | Yes |
| `POST` | `/api/v1/scraping/scrape-html` | Yes |
| `GET` | `/api/v1/llm/process-sample-documents` | Yes |
| `POST` | `/api/v1/llm/extract` | **No** — response only |
| `GET` | `/docs`, `/redoc` | No |

---

## Where output files are saved

| Path | Created by |
|------|------------|
| `data/etl/output_clean_data.json`, `data/etl/data_quality_report.txt` | ETL endpoints |
| `data/exchange/cache.json` | First exchange call; refreshed hourly |
| `data/scraping/extracted_documents.json` | Scraping endpoints |
| `data/llm/extracted_data.json`, `data/llm/comparison_report.md` | `GET /llm/process-sample-documents` only |
| `logs/scraping.log` | Task 3 |
| `logs/llm.log` | Task 4 batch |
| `logs/app.log` | App logging |

`POST /api/v1/llm/extract` returns JSON in the response only — use the batch endpoint to persist LLM output.

---

## Task 1 — ETL Pipeline

**Purpose:** Clean CSV (dates, numbers, duplicates); convert amounts to BGN; quality report.

| | |
|--|--|
| **Endpoints** | `POST /api/v1/etl/process-local-file`, `POST /api/v1/etl/upload` |
| **Input** | Default: `data/etl/dirty_financial_data.csv`. Columns: `date`, `company_id`, `revenue`, `expenses`, `currency`, `category` |
| **Output** | `data/etl/output_clean_data.json`, `data/etl/data_quality_report.txt` |
| **FX (ETL)** | EUR 1.96 · USD 1.80 · GBP 2.30 · BGN 1.00 |

```bash
curl -X POST http://localhost:8000/api/v1/etl/process-local-file
pytest tests/tasks/test_etl_task1.py tests/api/test_etl.py
```

Spec: `docs/assignment/Task_1_ETL_Pipeline/README.md`

---

## Task 2 — Exchange Rates

**Purpose:** Live EUR / USD / GBP vs BGN ([Exchangerate-API](https://www.exchangerate-api.com/)); 1-hour cache.

| | |
|--|--|
| **Endpoints** | `GET /api/v1/exchange/rates`, `GET /api/v1/exchange/convert?from_currency=&to_currency=&amount=` |
| **Input** | Query params for convert; currencies: `BGN`, `EUR`, `USD`, `GBP` |
| **Output** | JSON response + `data/exchange/cache.json` |

```bash
curl http://localhost:8000/api/v1/exchange/rates
curl "http://localhost:8000/api/v1/exchange/convert?from_currency=EUR&to_currency=BGN&amount=100"
pytest tests/tasks/test_exchange_client.py tests/api/test_exchange.py
```

Spec: `docs/assignment/Task_2_API_Integration/README.md`

---

## Task 3 — Document Scraping

**Purpose:** Find PDFs on pages (up to 20), download, extract metadata and 500-char preview; append to JSON.

| | |
|--|--|
| **Endpoints** | `GET /api/v1/scraping/process-local-urls`, `POST /api/v1/scraping/scrape-url`, `POST /api/v1/scraping/scrape-html` |
| **Input** | `data/scraping/sample_urls.txt`, single URL JSON, or saved HTML |
| **Output** | `data/scraping/extracted_documents.json`, `logs/scraping.log` |

```bash
curl http://localhost:8000/api/v1/scraping/process-local-urls
pytest tests/tasks/test_scraping_parsers.py tests/tasks/test_scraping_scraper.py \
  tests/tasks/test_scraping_task3.py tests/tasks/test_scraping_page_fetcher.py \
  tests/tasks/test_scraping_cloudflare.py tests/api/test_scraping.py
```

**Blocking / Cloudflare:** The scraper does not bypass protection; failures are logged in JSON and `logs/scraping.log`. Use `POST /scrape-html`, direct PDF URLs, offline fixture (`offline:data/scraping/fixtures/minfin_bg_1394_demo.html`), or optional Playwright (`SCRAPING_BROWSER_FALLBACK=true`, `playwright install chromium`) — no CAPTCHA/WAF bypass.

Spec: `docs/assignment/Task_3_Document_Scraping/README.md`

---

## Task 4 — LLM Data Extraction

**Purpose:** Extract `company_name`, `document_date`, `total_amount`, `currency`, categories, `financial_metrics`, and unit normalization fields from text.

| | |
|--|--|
| **Endpoints** | `GET /api/v1/llm/process-sample-documents` (writes files), `POST /api/v1/llm/extract` (response only) |
| **Input** | Batch: `docs/assignment/Task_4_LLM_Data_Extraction/sample_documents/*.txt`; ad-hoc: JSON `{"text": "..."}` |
| **Output** | Batch → `data/llm/extracted_data.json`, `data/llm/comparison_report.md`, `logs/llm.log` |

**Engine:** **OpenAI** when `OPENAI_API_KEY` is set (`extraction_method: openai`); otherwise deterministic **mock** rules (`mock`). Sample batch also runs regex comparison in `comparison_report.md`.

```bash
curl http://localhost:8000/api/v1/llm/process-sample-documents
pytest tests/tasks/test_llm_normalizer.py tests/tasks/test_llm_extractor.py tests/api/test_llm.py
```

Spec: `docs/assignment/Task_4_LLM_Data_Extraction/README.md`

**Config (`.env`):** `DATABASE_URL`, `ENVIRONMENT`, `LOG_LEVEL`, `OPENAPI_ENABLED`, `EXCHANGE_RATE_API_URL`, `SCRAPING_BROWSER_FALLBACK`, `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`). See `.env.example`.

---

## Tests

```bash
pytest
```

Covers ETL, exchange, scraping, LLM, and API routes.

---

## Deployment

**Production (Heroku):** https://www.financial-automation-platform.xyz/

Redeploy:

```bash
heroku config:set ENVIRONMENT=production DEBUG=false
git push heroku main
```

Uses `Procfile` (Gunicorn + Uvicorn) and `runtime.txt` (Python 3.11). For new apps: `heroku create your-app-name` then push. Consider PostgreSQL (`DATABASE_URL`) in production instead of SQLite.

---

## Project structure

**Flow:** HTTP (`api`, `web`) → `services` → `tasks` (+ `repositories` / SQLite when needed).

```
financial-automation-platform/
├── app/                         # FastAPI application
│   ├── main.py                  # App factory, lifespan, router mount
│   ├── api/
│   │   ├── router.py            # Aggregates v1 API routers
│   │   ├── deps.py              # Shared FastAPI dependencies
│   │   └── v1/                  # REST: health, etl, exchange, scraping, llm
│   ├── web/                     # Dashboard routes (HTML UI at /)
│   ├── templates/               # Jinja templates (dashboard.html)
│   ├── static/                  # Dashboard CSS, Swagger UI assets, favicon
│   ├── core/                    # config, database, logging, data_dirs, OpenAPI
│   ├── schemas/                 # Pydantic request/response models
│   ├── services/                # Orchestration over task modules
│   ├── repositories/            # Data access layer (SQLAlchemy)
│   ├── models/                  # ORM models
│   └── tasks/                   # Task implementations (assignment modules)
│       ├── etl/                 # Task 1 — CSV clean, transform, report
│       ├── exchange/            # Task 2 — live rates + file cache
│       ├── scraping/            # Task 3 — fetch, parse, PDF extract
│       └── llm/                 # Task 4 — OpenAI/mock extract, compare
├── tests/
│   ├── api/                     # Route tests (etl, exchange, scraping, llm, health, dashboard)
│   ├── tasks/                   # Unit/integration tests per task package
│   └── conftest.py
├── data/                        # Runtime outputs (gitignored; created on startup)
│   ├── etl/                     # Input CSV, cleaned JSON, quality report
│   ├── exchange/                # Rate cache
│   ├── scraping/                # URL list, fixtures, extracted_documents.json
│   ├── llm/                     # extracted_data.json, comparison_report.md
│   └── financial_data.db        # SQLite (local / default deploy)
├── docs/
│   ├── ARCHITECTURE.md          # Layers, design notes
│   └── assignment/              # Task_1 … Task_5 specs and sample inputs
├── logs/                        # app.log, scraping.log, llm.log (gitignored)
├── Procfile                     # Heroku: Gunicorn + Uvicorn workers
├── runtime.txt                  # Python 3.11
├── requirements.txt
├── pytest.ini
└── .env.example
```

| Layer | Role |
|-------|------|
| `api/v1` | JSON API and OpenAPI (`/docs`, `/redoc`) |
| `web` + `templates` + `static` | Browser dashboard at `/` |
| `services` | Calls `tasks/*`; shapes API responses |
| `tasks/*` | Core logic for each assignment task |
| `data/*` | Files written by ETL, exchange, scraping, LLM endpoints |

Further reading: `docs/ARCHITECTURE.md`, `docs/assignment/GENERAL_INSTRUCTIONS.md`.

---

## License

Internal / personal project.
