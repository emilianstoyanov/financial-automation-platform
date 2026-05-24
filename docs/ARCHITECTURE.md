# Architecture Overview

## Layers

```
┌─────────────────────────────────────────┐
│  API (app/api)          HTTP / OpenAPI  │
├─────────────────────────────────────────┤
│  Schemas (app/schemas)  Pydantic DTOs   │
├─────────────────────────────────────────┤
│  Services (app/services) Business logic │
├─────────────────────────────────────────┤
│  Repositories           Data access     │
├─────────────────────────────────────────┤
│  Models (app/models)    SQLAlchemy ORM  │
└─────────────────────────────────────────┘
         ▲                    ▲
         │                    │
    app/tasks/*          External APIs
    (batch / ETL)        (exchange, LLM, web)
```

## Core (`app/core`)

| Module | Responsibility |
|--------|----------------|
| `config.py` | Environment-based settings via `pydantic-settings` |
| `database.py` | SQLAlchemy engine, session, `Base`, `init_db()` |
| `logging_config.py` | Console + rotating file logging |
| `data_dirs.py` | Local `data/` layout (`etl/`, `exchange/`, etc.) |

## Local data (`data/`)

| Path | Purpose |
|------|---------|
| `data/etl/` | ETL CSV input and cleaned JSON / quality report |
| `data/exchange/` | Exchange rate cache (future tasks) |
| `data/scraping/` | Scraped documents metadata (future tasks) |
| `data/llm/` | LLM extraction output (future tasks) |
| `data/financial_data.db` | SQLite application database |

Directories are created on application startup via `ensure_data_directories()`.

## Task modules (`app/tasks`)

Placeholder packages aligned with interview assignments:

- `etl/` — financial data pipelines
- `exchange/` — exchange rate API client
- `scraping/` — document/metadata extraction
- `llm/` — LLM-assisted structured extraction

## Design principles

- **Dependency inversion**: API depends on services; services depend on repository abstractions.
- **Single responsibility**: Each package has one reason to change.
- **Configuration**: No hardcoded secrets; use `.env` / Heroku config vars.

## Deployment (Heroku)

- `Procfile` runs Gunicorn with Uvicorn workers.
- `DATABASE_URL` is normalized for PostgreSQL when upgrading from SQLite.
- `runtime.txt` pins Python 3.11.
