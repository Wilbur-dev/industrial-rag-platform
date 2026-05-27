"""Structured application errors — Week 2 Day 5."""

from typing import Any


class AppError(Exception):
    """Base error with HTTP mapping and machine-readable code."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            body["details"] = self.details
        return body


class ValidationError(AppError):
    status_code = 400
    error_code = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class IngestionError(AppError):
    status_code = 400
    error_code = "ingestion_error"


class RetrievalError(AppError):
    status_code = 503
    error_code = "retrieval_error"


class GenerationError(AppError):
    status_code = 502
    error_code = "generation_error"


class EvaluationError(AppError):
    status_code = 400
    error_code = "evaluation_error"
