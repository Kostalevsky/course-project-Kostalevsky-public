import re
import uuid
from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse


def mask_error_details(message: str) -> str:
    """
    Маскирует чувствительную информацию в сообщениях об ошибках.
    """
    patterns = [
        (r"password[:\s]+\S+", "password: [REDACTED]"),
        (r"token[:\s]+\S+", "token: [REDACTED]"),
        (r"secret[:\s]+\S+", "secret: [REDACTED]"),
        (r"file://[^\s]+", "file://[REDACTED]"),
        (r"localhost:\d+", "[REDACTED]"),
        (r"127\.0\.0\.1:\d+", "[REDACTED]"),
    ]

    masked = message
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)

    return masked


def problem(
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    instance: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> JSONResponse:
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    payload = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "correlation_id": correlation_id,
    }

    if instance:
        payload["instance"] = instance

    if extras:
        payload.update(extras)

    return JSONResponse(
        status_code=status,
        content=payload,
        headers={"X-Correlation-ID": correlation_id},
    )


def validation_error(
    detail: str, field: Optional[str] = None, instance: Optional[str] = None
) -> JSONResponse:
    extras = {}
    if field:
        extras["field"] = field

    return problem(
        status=422,
        title="Validation Error",
        detail=detail,
        type_uri="https://api.learning-flashcards.com/problems/validation-error",
        instance=instance,
        extras=extras,
    )


def not_found_error(
    resource: str, resource_id: str, instance: Optional[str] = None
) -> JSONResponse:
    return problem(
        status=404,
        title="Resource Not Found",
        detail=f"{resource} with id '{resource_id}' not found",
        type_uri="https://api.learning-flashcards.com/problems/not-found",
        instance=instance,
    )


def rate_limit_error(limit: int, window: str, instance: Optional[str] = None) -> JSONResponse:
    return problem(
        status=429,
        title="Too Many Requests",
        detail=f"{limit} requests per {window}",
        type_uri="https://api.learning-flashcards.com/problems/rate-limit-exceeded",
        instance=instance,
        extras={"limit": limit, "window": window, "retry_after": 60},
    )


def internal_error(
    detail: str = "An internal server error occurred", instance: Optional[str] = None
) -> JSONResponse:
    # Маскируем чувствительную информацию
    masked_detail = detail
    if "password" in detail.lower():
        masked_detail = "An internal server error occurred"
    elif "secret" in detail.lower():
        masked_detail = "An internal server error occurred"
    elif "key" in detail.lower():
        masked_detail = "An internal server error occurred"

    return problem(
        status=500,
        title="Internal Server Error",
        detail=masked_detail,
        type_uri="https://api.learning-flashcards.com/problems/internal-error",
        instance=instance,
    )
