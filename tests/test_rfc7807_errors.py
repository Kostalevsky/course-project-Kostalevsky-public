import json

from app.errors import internal_error, not_found_error, problem, rate_limit_error, validation_error


class TestProblemFunction:

    def test_basic_problem_structure(self):
        response = problem(
            status=400,
            title="Bad Request",
            detail="Invalid request data",
            type_uri="https://api.example.com/problems/bad-request",
        )

        assert response.status_code == 400
        content = json.loads(response.body)

        assert "type" in content
        assert "title" in content
        assert "status" in content
        assert "detail" in content
        assert "correlation_id" in content

        assert content["type"] == "https://api.example.com/problems/bad-request"
        assert content["title"] == "Bad Request"
        assert content["status"] == 400
        assert content["detail"] == "Invalid request data"
        assert "correlation_id" in content

    def test_problem_with_instance(self):
        response = problem(
            status=404,
            title="Not Found",
            detail="Resource not found",
            instance="/api/users/123",
        )

        content = json.loads(response.body)
        assert content["instance"] == "/api/users/123"

    def test_problem_with_extras(self):
        response = problem(
            status=422,
            title="Validation Error",
            detail="Invalid data",
            extras={"field": "email", "code": "INVALID_EMAIL"},
        )

        content = json.loads(response.body)
        assert content["field"] == "email"
        assert content["code"] == "INVALID_EMAIL"

    def test_problem_correlation_id_header(self):
        response = problem(status=500, title="Internal Error", detail="Something went wrong")

        content = json.loads(response.body)
        correlation_id = content["correlation_id"]

        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == correlation_id

    def test_problem_unique_correlation_ids(self):
        response1 = problem(status=400, title="Error 1", detail="Detail 1")
        response2 = problem(status=400, title="Error 2", detail="Detail 2")

        content1 = json.loads(response1.body)
        content2 = json.loads(response2.body)

        assert content1["correlation_id"] != content2["correlation_id"]


class TestValidationError:

    def test_validation_error_basic(self):
        response = validation_error("Email is required")

        assert response.status_code == 422
        content = json.loads(response.body)

        assert content["type"] == "https://api.learning-flashcards.com/problems/validation-error"
        assert content["title"] == "Validation Error"
        assert content["status"] == 422
        assert content["detail"] == "Email is required"

    def test_validation_error_with_field(self):
        response = validation_error(
            detail="Invalid email format", field="email", instance="/api/users"
        )

        content = json.loads(response.body)
        assert content["field"] == "email"
        assert content["instance"] == "/api/users"

    def test_validation_error_without_field(self):
        response = validation_error("General validation error")

        content = json.loads(response.body)
        assert "field" not in content


class TestNotFoundError:

    def test_not_found_error_basic(self):
        response = not_found_error("user", "123")

        assert response.status_code == 404
        content = json.loads(response.body)

        assert content["type"] == "https://api.learning-flashcards.com/problems/not-found"
        assert content["title"] == "Resource Not Found"
        assert content["status"] == 404
        assert "user with id '123' not found" in content["detail"]

    def test_not_found_error_with_instance(self):
        response = not_found_error("deck", "abc-123", "/api/decks/abc-123")

        content = json.loads(response.body)
        assert content["instance"] == "/api/decks/abc-123"
        assert "deck with id 'abc-123' not found" in content["detail"]


class TestRateLimitError:

    def test_rate_limit_error_basic(self):
        response = rate_limit_error(limit=100, window="1m")

        assert response.status_code == 429
        content = json.loads(response.body)

        assert content["type"] == "https://api.learning-flashcards.com/problems/rate-limit-exceeded"
        assert content["title"] == "Too Many Requests"
        assert content["status"] == 429
        assert "100 requests per 1m" in content["detail"]
        assert content["limit"] == 100
        assert content["window"] == "1m"
        assert content["retry_after"] == 60

    def test_rate_limit_error_with_instance(self):
        response = rate_limit_error(limit=10, window="1h", instance="/api/decks")

        content = json.loads(response.body)
        assert content["instance"] == "/api/decks"
        assert "10 requests per 1h" in content["detail"]


class TestInternalError:

    def test_internal_error_basic(self):
        response = internal_error()

        assert response.status_code == 500
        content = json.loads(response.body)

        assert content["type"] == "https://api.learning-flashcards.com/problems/internal-error"
        assert content["title"] == "Internal Server Error"
        assert content["status"] == 500
        assert "internal server error" in content["detail"].lower()

    def test_internal_error_custom_detail(self):
        response = internal_error(detail="Database connection failed", instance="/api/decks")

        content = json.loads(response.body)
        assert content["detail"] == "Database connection failed"
        assert content["instance"] == "/api/decks"


class TestRFC7807Compliance:

    def test_all_required_fields_present(self):
        response = problem(status=400, title="Test Error", detail="Test detail")

        content = json.loads(response.body)
        required_fields = ["type", "title", "status", "detail"]

        for field in required_fields:
            assert field in content, f"Required field '{field}' is missing"

    def test_status_code_matches_content(self):
        response = problem(status=422, title="Validation Error", detail="Invalid data")

        assert response.status_code == 422
        content = json.loads(response.body)
        assert content["status"] == 422

    def test_type_uri_format(self):
        response = problem(
            status=400,
            title="Error",
            detail="Detail",
            type_uri="https://api.example.com/problems/test",
        )

        content = json.loads(response.body)
        type_uri = content["type"]
        assert type_uri.startswith("https://")
        assert "problems/" in type_uri

    def test_correlation_id_format(self):
        response = problem(status=400, title="Error", detail="Detail")

        content = json.loads(response.body)
        correlation_id = content["correlation_id"]

        assert len(correlation_id) == 36
        assert correlation_id.count("-") == 4
        assert correlation_id[14] == "4"  # UUID4 версия


class TestErrorMasking:

    def test_internal_error_masks_details(self):
        response = internal_error(detail="Database password: secret123")

        content = json.loads(response.body)
        assert "secret123" not in content["detail"]

    def test_validation_error_preserves_safe_details(self):
        response = validation_error("Field 'email' is required")

        content = json.loads(response.body)
        assert "email" in content["detail"]  # Безопасная информация
        assert "required" in content["detail"]
