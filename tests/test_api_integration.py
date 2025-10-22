"""
Интеграционные тесты для API с применением всех ADR.

Покрывает:
- ADR-001: Валидация ввода и защита от path traversal
- ADR-002: Стандартизация обработки ошибок по RFC 7807
- ADR-003: Rate Limiting и защита от перегрузки
"""

import uuid


class TestValidationIntegration:
    """Тесты валидации в интеграции с API."""

    def test_valid_deck_creation(self, client):
        """Тест создания валидной колоды."""
        response = client.post("/decks", json={"name": "Test Deck", "description": "A test deck"})

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Deck"

        # Проверяем что ID является валидным UUID
        deck_id = data["id"]
        uuid.UUID(deck_id)  # Не должно вызывать исключение

    def test_invalid_deck_id_format(self, client):
        """Тест невалидного формата ID колоды."""
        invalid_id = "not-a-uuid"

        response = client.get(f"/decks/{invalid_id}")

        assert response.status_code == 422
        data = response.json()

        # Проверяем RFC 7807 формат
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "correlation_id" in data
        assert data["status"] == 422
        assert "Invalid deck ID format" in data["detail"]

    def test_invalid_card_id_format(self, client):
        """Тест невалидного формата ID карточки."""
        # Сначала создаем колоду
        # deck_response = client.post(
        #     "/decks", json={"name": "Test Deck", "description": "A test deck"}
        # )
        # deck_id = deck_response.json()["id"]

        # Создаем карточку с невалидным ID
        response = client.post("/reviews", json={"card_id": "not-a-uuid", "grade": "good"})

        assert response.status_code == 422
        data = response.json()

        # Проверяем RFC 7807 формат
        assert data["status"] == 422
        assert "card_id" in data["detail"]

    # def test_deck_not_found(self):
    #     """Тест ошибки 'колода не найдена'."""
    #     non_existent_id = str(uuid.uuid4())

    #     response = client.get(f"/decks/{non_existent_id}")

    #     assert response.status_code == 404
    #     data = response.json()

    #     # Проверяем RFC 7807 формат
    #     assert data["status"] == 404
    #     assert "deck not found" in data["detail"]
    #     assert "correlation_id" in data


class TestRFC7807Integration:
    """Тесты RFC 7807 в интеграции с API."""

    def test_validation_error_format(self, client):
        """Тест формата ошибки валидации."""
        response = client.post(
            "/decks",
            json={
                "name": "",  # Пустое имя должно вызвать ошибку валидации
                "description": "A test deck",
            },
        )

        assert response.status_code == 422
        data = response.json()

        # Проверяем RFC 7807 структуру
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "correlation_id" in data
        assert "instance" in data

        # Проверяем заголовки
        assert "X-Correlation-ID" in response.headers

    # def test_not_found_error_format(self):
    #     """Тест формата ошибки 'не найдено'."""
    #     non_existent_id = str(uuid.uuid4())

    #     response = client.get(f"/decks/{non_existent_id}")

    #     assert response.status_code == 404
    #     data = response.json()

    #     # Проверяем RFC 7807 структуру
    #     assert data["type"] == "https://api.learning-flashcards.com/problems/api-error"
    #     assert data["title"] == "API Error"
    #     assert data["status"] == 404
    #     assert "not found" in data["detail"]
    #     assert "correlation_id" in data

    def test_correlation_id_consistency(self, client):
        """Тест консистентности correlation ID."""
        non_existent_id = str(uuid.uuid4())
        response = client.get(f"/decks/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()

        # Correlation ID в теле ответа и заголовке должны совпадать
        body_cid = data["correlation_id"]
        header_cid = response.headers["X-Correlation-ID"]

        assert body_cid == header_cid
        assert body_cid is not None
        assert len(body_cid) > 0


class TestRateLimitingIntegration:
    """Тесты rate limiting в интеграции с API."""

    def test_normal_request_allowed(self, client):
        """Тест что обычные запросы разрешены."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_multiple_requests(self, client):
        """Тест множественных запросов."""
        # Делаем несколько запросов подряд
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_deck_creation_validation(self, client):
        """Тест валидации при создании колоды."""
        # Валидная колода
        response = client.post("/decks", json={"name": "Valid Deck", "description": "A valid deck"})
        assert response.status_code == 201

        # Невалидная колода (пустое имя)
        response = client.post("/decks", json={"name": "", "description": "Invalid deck"})
        assert response.status_code == 422

        # Проверяем RFC 7807 формат
        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "correlation_id" in data


class TestCardOperations:
    """Тесты операций с карточками."""

    # def test_create_card_in_valid_deck(self):
    #     """Тест создания карточки в валидной колоде."""
    #     # Создаем колоду
    #     deck_response = client.post("/decks", json={
    #         "name": "Test Deck",
    #         "description": "A test deck"
    #     })
    #     deck_id = deck_response.json()["id"]

    #     # Создаем карточку
    #     response = client.post(f"/decks/{deck_id}/cards", json={
    #         "front": "What is Python?",
    #         "back": "A programming language",
    #         "hint": "Think of a snake"
    #     })

    #     assert response.status_code == 201
    #     data = response.json()
    #     assert data["front"] == "What is Python?"
    #     assert data["back"] == "A programming language"
    #     assert data["hint"] == "Think of a snake"
    #     assert data["deck_id"] == deck_id

    # def test_create_card_in_invalid_deck(self):
    #     """Тест создания карточки в несуществующей колоде."""
    #     non_existent_id = str(uuid.uuid4())

    #     response = client.post(f"/decks/{non_existent_id}/cards", json={
    #         "front": "What is Python?",
    #         "back": "A programming language"
    #     })

    #     assert response.status_code == 404
    #     data = response.json()
    #     assert "deck not found" in data["detail"]

    def test_get_random_card_from_empty_deck(self, client):
        """Тест получения случайной карточки из пустой колоды."""
        # Создаем колоду
        deck_response = client.post(
            "/decks", json={"name": "Empty Deck", "description": "An empty deck"}
        )
        deck_id = deck_response.json()["id"]

        # Пытаемся получить случайную карточку
        response = client.get(f"/decks/{deck_id}/cards/random")

        assert response.status_code == 404
        data = response.json()
        assert "no cards in deck" in data["detail"]


class TestReviewOperations:
    """Тесты операций с повторениями."""

    def test_review_valid_card(self, client):
        """Тест повторения валидной карточки."""
        # Создаем колоду и карточку
        deck_response = client.post(
            "/decks", json={"name": "Test Deck", "description": "A test deck"}
        )
        deck_id = deck_response.json()["id"]

        card_response = client.post(
            f"/decks/{deck_id}/cards",
            json={"front": "What is Python?", "back": "A programming language"},
        )
        card_id = card_response.json()["id"]

        # Делаем повторение
        response = client.post("/reviews", json={"card_id": card_id, "grade": "good"})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == card_id
        assert "ease" in data
        assert "interval_days" in data
        assert "due_at" in data

    # def test_review_invalid_card(self):
    #     """Тест повторения несуществующей карточки."""
    #     non_existent_id = str(uuid.uuid4())

    #     response = client.post("/reviews", json={
    #         "card_id": non_existent_id,
    #         "grade": "good"
    #     })

    #     assert response.status_code == 404
    #     data = response.json()
    #     assert "card not found" in data["detail"]

    def test_review_invalid_grade(self, client):
        """Тест повторения с невалидной оценкой."""
        # Создаем колоду и карточку
        deck_response = client.post(
            "/decks", json={"name": "Test Deck", "description": "A test deck"}
        )
        deck_id = deck_response.json()["id"]

        card_response = client.post(
            f"/decks/{deck_id}/cards",
            json={"front": "What is Python?", "back": "A programming language"},
        )
        card_id = card_response.json()["id"]

        # Пытаемся использовать невалидную оценку
        response = client.post("/reviews", json={"card_id": card_id, "grade": "invalid_grade"})

        assert response.status_code == 422
        data = response.json()
        assert "status" in data
        assert "detail" in data


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_very_long_deck_name(self, client):
        """Тест очень длинного имени колоды."""
        long_name = "x" * 101  # Превышает лимит в 100 символов

        response = client.post("/decks", json={"name": long_name, "description": "A test deck"})

        assert response.status_code == 422
        data = response.json()
        assert "status" in data
        assert "detail" in data

    def test_very_long_card_content(self, client):
        """Тест очень длинного содержимого карточки."""
        # Создаем колоду
        deck_response = client.post(
            "/decks", json={"name": "Test Deck", "description": "A test deck"}
        )
        deck_id = deck_response.json()["id"]

        long_content = "x" * 201  # Превышает лимит в 200 символов

        response = client.post(
            f"/decks/{deck_id}/cards",
            json={"front": long_content, "back": "A programming language"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "status" in data
        assert "detail" in data

    def test_unicode_content(self, client):
        """Тест Unicode содержимого."""
        # Создаем колоду
        deck_response = client.post(
            "/decks",
            json={"name": "Тестовая колода", "description": "Колода для тестирования"},
        )
        deck_id = deck_response.json()["id"]

        # Создаем карточку с Unicode содержимым
        response = client.post(
            f"/decks/{deck_id}/cards",
            json={
                "front": "Что такое Python?",
                "back": "Язык программирования",
                "hint": "Думай о змее",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["front"] == "Что такое Python?"
        assert data["back"] == "Язык программирования"
        assert data["hint"] == "Думай о змее"
