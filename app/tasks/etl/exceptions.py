"""ETL-specific exceptions."""


class ETLError(Exception):
    """Base exception for ETL operations."""


class ETLFileNotFoundError(ETLError):
    """Raised when the input CSV file does not exist."""


class ETLProcessingError(ETLError):
    """Raised when the ETL pipeline fails unexpectedly."""


class ETLInvalidFileTypeError(ETLError):
    """Raised when an uploaded file is not a CSV."""


class ETLEmptyFileError(ETLError):
    """Raised when an uploaded file has no content."""
