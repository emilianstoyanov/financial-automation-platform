"""Exchange rate API exceptions."""


class ExchangeError(Exception):
    """Base exception for exchange rate operations."""


class ExchangeTimeoutError(ExchangeError):
    """Raised when the external API request times out."""


class ExchangeNetworkError(ExchangeError):
    """Raised on connection or transport failures."""


class ExchangeAPIError(ExchangeError):
    """Raised when the API returns an HTTP error or rate limit."""


class ExchangeInvalidResponseError(ExchangeError):
    """Raised when the API response is not valid JSON or is malformed."""


class ExchangeCurrencyNotFoundError(ExchangeError):
    """Raised when a requested currency is missing from the rate data."""
