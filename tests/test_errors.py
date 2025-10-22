# """
# Тесты для модуля обработки ошибок RFC 7807.
#
# Покрывает ADR-002: Стандартизация обработки ошибок по RFC 7807.
# """
import json
import uuid

from app.errors import (
    internal_error,
    mask_error_details,
    problem,
    rate_limit_error,
    validation_error,
)


class TestRFC7807Format:
    """Тесты формата RFC 7807."""

    def test_problem_response_structure(self):
        """Тест структуры ответа problem_response."""
        response = problem(
            status=422,
            title="Validation Error",
            detail="Input validation failed",
            type_uri="https://api.learning-flashcards.com/problems/validation-error",
            instance="/api/decks/123",
        )

        assert response.status_code == 422

        content = json.loads(response.body.decode())
        assert content["type"] == "https://api.learning-flashcards.com/problems/validation-error"
        assert content["title"] == "Validation Error"
        assert content["status"] == 422
        assert content["detail"] == "Input validation failed"
        assert content["instance"] == "/api/decks/123"
        assert "correlation_id" in content
        assert "X-Correlation-ID" in response.headers

    def test_validation_error_response(self):
        """Тест ответа об ошибке валидации."""
        response = validation_error(
            detail="Invalid deck ID format", instance="/api/decks/invalid-id"
        )

        assert response.status_code == 422

        content = json.loads(response.body.decode())
        assert content["type"] == "https://api.learning-flashcards.com/problems/validation-error"
        assert content["title"] == "Validation Error"
        assert content["status"] == 422
        assert content["detail"] == "Invalid deck ID format"
        assert content["instance"] == "/api/decks/invalid-id"

    # def test_not_found_error_response(self):
    #     """Тест ответа об ошибке 'не найдено'."""
    #     response = not_found_error(
    #         resource="Deck",
    #         resource_id="123",
    #         instance="/api/decks/123"
    #     )

    #     assert response.status_code == 404

    #     content = json.loads(response.body.decode())
    #     assert content["type"] == "https://api.learning-flashcards.com/problems/not-found"
    #     assert content["title"] == "Resource Not Found"
    #     assert content["status"] == 404
    #     assert content["detail"] == "Deck not found"

    def test_internal_error_response(self):
        """Тест ответа о внутренней ошибке."""
        response = internal_error(detail="Internal server error", instance="/api/decks/123")

        assert response.status_code == 500

        content = json.loads(response.body.decode())
        assert content["type"] == "https://api.learning-flashcards.com/problems/internal-error"
        assert content["title"] == "Internal Server Error"
        assert content["status"] == 500
        assert content["detail"] == "Internal server error"

    def test_rate_limit_error_response(self):
        """Тест ответа об ошибке rate limit."""
        response = rate_limit_error(limit=100, window="1m", instance="/api/decks")

        assert response.status_code == 429

        content = json.loads(response.body.decode())
        assert content["type"] == "https://api.learning-flashcards.com/problems/rate-limit-exceeded"
        assert content["title"] == "Too Many Requests"
        assert content["status"] == 429
        assert content["detail"] == "100 requests per 1m"
        assert content["retry_after"] == 60

    # def test_correlation_id_generation(self):
    #     """Тест генерации correlation ID."""
    #     cid1 = generate_correlation_id()
    #     cid2 = generate_correlation_id()
    #
    #     # Проверяем что это валидные UUID
    #     uuid.UUID(cid1)
    #     uuid.UUID(cid2)
    #
    #     # Проверяем что они разные
    #     assert cid1 != cid2

    def test_custom_correlation_id(self):
        """Тест использования кастомного correlation ID."""
        custom_cid = str(uuid.uuid4())

        response = problem(
            status=400,
            title="Bad Request",
            detail="Invalid request",
            correlation_id=custom_cid,
        )

        content = json.loads(response.body.decode())
        assert content["correlation_id"] == custom_cid
        assert response.headers["X-Correlation-ID"] == custom_cid

    # class TestErrorMasking:
    """Тесты маскирования ошибок."""

    def test_mask_password_in_error(self):
        """Тест маскирования пароля в ошибке."""
        error_msg = "Invalid password: secret123"
        masked = mask_error_details(error_msg)

        assert "secret123" not in masked
        assert "[REDACTED]" in masked

    def test_mask_token_in_error(self):
        """Тест маскирования токена в ошибке."""
        error_msg = "Invalid token: abc123def456"
        masked = mask_error_details(error_msg)

        assert "abc123def456" not in masked
        assert "[REDACTED]" in masked

    def test_mask_file_path_in_error(self):
        """Тест маскирования пути к файлу в ошибке."""
        error_msg = "Cannot access file:///etc/passwd"
        masked = mask_error_details(error_msg)

        assert "/etc/passwd" not in masked
        assert "[REDACTED]" in masked

    def test_mask_localhost_in_error(self):
        """Тест маскирования localhost в ошибке."""
        error_msg = "Connection failed to localhost:8080"
        masked = mask_error_details(error_msg)

        assert "localhost" not in masked
        assert "[REDACTED]" in masked

    def test_no_masking_for_safe_content(self):
        """Тест что безопасный контент не маскируется."""
        safe_msg = "Deck not found with ID 123"
        masked = mask_error_details(safe_msg)

        assert masked == safe_msg

    # def test_multiple_sensitive_patterns(self):
    #     """Тест маскирования нескольких чувствительных паттернов."""
    #     error_msg = "Failed to connect to localhost with password: secret123"
    #     masked = mask_error_details(error_msg)

    #     assert "localhost" not in masked
    #     assert "secret123" not in masked
    #     assert "[REDACTED]" in masked


class TestErrorResponseIntegration:
    """Тесты интеграции с FastAPI."""

    def test_error_response_headers(self):
        """Тест заголовков в ответе об ошибке."""
        response = problem(status=422, title="Validation Error", detail="Input validation failed")

        assert "X-Correlation-ID" in response.headers
        assert "Content-Type" in response.headers
        assert response.headers["Content-Type"] == "application/json"

    def test_error_response_extras(self):
        """Тест дополнительных полей в ответе."""
        extras = {"field": "deck_id", "code": "INVALID_FORMAT"}

        response = problem(
            status=422,
            title="Validation Error",
            detail="Invalid deck ID",
            extras=extras,
        )

        content = json.loads(response.body.decode())
        assert content["field"] == "deck_id"
        assert content["code"] == "INVALID_FORMAT"

    def test_error_response_without_instance(self):
        """Тест ответа без instance."""
        response = problem(status=500, title="Internal Error", detail="Something went wrong")

        content = json.loads(response.body.decode())
        assert "instance" not in content
        assert "correlation_id" in content


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_detail(self):
        """Тест пустого detail."""
        response = problem(status=400, title="Bad Request", detail="")

        content = json.loads(response.body.decode())
        assert content["detail"] == ""

    def test_very_long_detail(self):
        """Тест очень длинного detail."""
        long_detail = "x" * 10000

        response = problem(status=400, title="Bad Request", detail=long_detail)

        content = json.loads(response.body.decode())
        assert content["detail"] == long_detail

    def test_unicode_in_detail(self):
        """Тест Unicode символов в detail."""
        unicode_detail = "Ошибка валидации: неверный формат ID"

        response = problem(status=422, title="Validation Error", detail=unicode_detail)

        content = json.loads(response.body.decode())
        assert content["detail"] == unicode_detail

    def test_none_values(self):
        """Тест None значений."""
        response = problem(
            status=400,
            title="Bad Request",
            detail="Error",
            instance=None,
            correlation_id=None,
        )

        content = json.loads(response.body.decode())
        assert "instance" not in content
        assert "correlation_id" in content  # Должен быть сгенерирован
