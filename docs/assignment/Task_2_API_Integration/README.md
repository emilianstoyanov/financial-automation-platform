# Task 2: API Integration

## Description
Create a Python script that integrates with an external API for financial data.

## API Options (accessible from Bulgaria)
Choose one of the following free APIs:

1. **Exchangerate-API** (recommended)
   - URL: https://api.exchangerate-api.com/v4/latest/BGN
   - Free, no registration required
   - Returns exchange rates

2. **frankfurter.app**
   - URL: https://api.frankfurter.app/latest?from=BGN
   - Free, no registration required
   - European exchange rates

## Your Task
Create a script that:

1. **Data Retrieval**
   - Makes requests to the chosen API
   - Retrieves rates for at least EUR, USD, GBP against BGN

2. **Rate Limiting**
   - Implement mechanism to prevent too many requests
   - Add delay between requests if making multiple calls

3. **Retry Logic**
   - On failed request, retry up to 3 times with exponential backoff
   - Handle timeout errors

4. **Caching**
   - Save results locally (JSON file)
   - If data is less than 1 hour old, use cache instead of new API call
   - Add timestamp to cached data

5. **Error Handling**
   - HTTP errors (404, 500, etc.)
   - Network timeouts
   - Invalid JSON responses
   - API rate limit errors
   
6. **Additional Requirements**
   - Create unit tests for core functions

## Expected Files
- `api_client.py` - main script with API client class
- `cache.json` - cache file (will be generated automatically)
- `example_usage.py` - example of how to use your API client
- `tests.py` - unit tests

## Example Structure
```python
class ExchangeRateClient:
    def __init__(self, base_currency='BGN', cache_file='cache.json'):
        ...
    
    def get_rates(self, currencies=None):
        ...
    
    def _fetch_from_api(self):
        ...
    
    def _is_cache_valid(self):
        ...
```

## Evaluation Criteria
- Proper implementation of retry logic
- Effective caching
- Robust error handling
- Clean and maintainable code
- Good documentation
