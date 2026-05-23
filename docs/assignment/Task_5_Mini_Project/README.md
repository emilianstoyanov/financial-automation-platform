# Task 5: End-to-End Mini Project

## Description
Create a complete ETL pipeline for a daily-updated financial dashboard.

## Scenario
The company needs a system that:
- Collects exchange rates daily
- Aggregates financial news from RSS feeds
- Provides data via REST API
- (Optional) Visualizes the data

## System Components

### 1. Data Collection
Create module to collect data from:
- **Exchangerate API** - exchange rates (BGN/EUR/USD/GBP)
- **RSS Feeds** - financial news (e.g., from BNB, Capital, Investor.bg)

### 2. Data Processing
- Validate collected data
- Normalize formats
- Enrich data (e.g., add timestamps, source metadata)
- Calculate daily changes in rates

### 3. Data Storage
- SQLite database with following tables:
  - `exchange_rates` - historical exchange rates
  - `news` - financial news
  - `metadata` - last update information

### 4. API Endpoint
Create simple Flask/FastAPI endpoint:
```
GET /api/rates - current exchange rates
GET /api/rates/history?days=7 - historical data
GET /api/news?limit=10 - recent news
GET /api/health - system status
```

### 5. Scheduler
- Implement automatic data updates
- Can use schedule library or cron

## Project Structure
```
mini_project/
├── src/
│   ├── collectors/
│   │   ├── exchange_rate_collector.py
│   │   └── news_collector.py
│   ├── processors/
│   │   └── data_processor.py
│   ├── storage/
│   │   └── database.py
│   └── api/
│       └── app.py
├── tests/
│   └── test_collectors.py
├── data/
│   └── financial_data.db
├── config.py
├── main.py
└── README.md
```

## Expected Functionality

**Must Have:**
- Data collection from 2+ sources
- Data validation and processing
- SQLite storage
- Basic REST API
- Error handling and logging
- Documentation
- Unit tests

**Nice to Have:**
- Scheduler for automatic updates
- Simple web UI for visualization
- Configuration management

## Technical Requirements

1. **Code Quality**
   - Good structure and organization
   - Clear naming conventions
   - Docstrings and comments
   - Type hints

2. **Error Handling**
   - Graceful handling of API failures
   - Database connection errors
   - Invalid data formats

3. **Logging**
   - Structured logging
   - Different log levels
   - Log rotation

4. **Configuration**
   - External config file
   - Don't hardcode API keys or sensitive data

## Notes
- Focus on quality, not quantity of features
- Production-ready code
- Document your design decisions
- If something is unclear, make reasonable assumptions and document them
