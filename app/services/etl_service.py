"""Service layer for ETL operations."""

import tempfile
from pathlib import Path
from app.tasks.etl.models import ETLResult
from app.tasks.etl.pipeline import ETLPipelineService
from app.core.logging_config import get_logger
from app.tasks.etl.constants import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_QUALITY_REPORT,
)
from app.tasks.etl.exceptions import (
    ETLEmptyFileError,
    ETLFileNotFoundError,
    ETLInvalidFileTypeError,
)

logger = get_logger(__name__)


class ETLApplicationService:
    """Facade for running ``ETLPipelineService`` from HTTP handlers."""

    def __init__(
            self,
            input_path: str | Path = DEFAULT_INPUT_FILE,
            output_json_path: str | Path = DEFAULT_OUTPUT_JSON,
            report_path: str | Path = DEFAULT_QUALITY_REPORT,
    ) -> None:
        """Wire pipeline paths; outputs default to ``data/etl/``."""
        self._pipeline = ETLPipelineService(
            input_path=input_path,
            output_json_path=output_json_path,
            report_path=report_path,
        )

    def process_local_file(self, persist: bool = True) -> ETLResult:
        """Process the configured local CSV (default: ``data/etl/dirty_financial_data.csv``)."""
        logger.info("Processing local ETL file: %s", self._pipeline.input_path)
        if not self._pipeline.input_path.is_file():
            raise ETLFileNotFoundError(
                f"Local ETL file not found: {self._pipeline.input_path}"
            )
        return self._pipeline.run(persist=persist)

    def process_upload(
            self,
            filename: str | None,
            content: bytes,
            persist: bool = True,
    ) -> ETLResult:
        """Validate upload, run pipeline on a temp file, write results under ``data/etl/``."""
        self._validate_upload(filename, content)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb",
                    suffix=".csv",
                    delete=False,
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)

            logger.info("Processing uploaded ETL file: %s", filename)
            pipeline = ETLPipelineService(
                input_path=temp_path,
                output_json_path=self._pipeline.output_json_path,
                report_path=self._pipeline.report_path,
            )
            return pipeline.run(persist=persist)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _validate_upload(filename: str | None, content: bytes) -> None:
        """Raise ``ETLInvalidFileTypeError`` or ``ETLEmptyFileError`` when upload is invalid."""
        if not filename or not filename.lower().endswith(".csv"):
            raise ETLInvalidFileTypeError("Only .csv files are allowed")

        if not content or not content.strip():
            raise ETLEmptyFileError("Uploaded file is empty")
