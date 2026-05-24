"""LLM extraction exceptions."""


class LLMExtractionError(Exception):
    """Base exception for LLM extraction operations."""


class LLMDocumentNotFoundError(LLMExtractionError):
    """Raised when a sample document file is missing."""


class LLMAPIError(LLMExtractionError):
    """Raised when the OpenAI API call fails."""
