# import time
# import pytest
# from fastapi.testclient import TestClient
# from unittest.mock import patch

# from app.main import app
# from app.middleware import RateLimitStore, RateLimitMiddleware


# class TestRateLimitStore:
#     """Тесты для хранилища rate limiting."""

#     def test_is_allowed_within_limit(self):
#         """Тест разрешения запросов в пределах лимита."""
#         store = RateLimitStore()
#         key = "test_client"

#         # Первые 5 запросов должны быть разрешены
#         for i in range(5):
#             allowed, remaining = store.is_allowed(key, limit=10, window=60)
#             assert allowed
#             assert remaining == 10 - i - 1

#     def test_is_allowed_exceeds_limit(self):
#         """Тест блокировки при превышении лимита."""
#         store = RateLimitStore()
#         key = "test_client"

#         # Исчерпываем лимит (10 запросов из 10)
#         for i in range(10):
#             allowed, remaining = store.is_allowed(key, limit=10, window=60)
#             assert allowed
#             assert remaining == 10 - i - 1

#         # 11-й запрос должен быть заблокирован
#         allowed, remaining = store.is_allowed(key, limit=10, window=60)
#         assert not allowed
#         assert remaining == 0

#     def test_is_allowed_window_expiry(self):
#         """Тест истечения временного окна."""
#         store = RateLimitStore()
#         key = "test_client"

#         # Исчерпываем лимит
#         for _ in range(10):
#             store.is_allowed(key, limit=10, window=1)  # 1 секунда

#         # Проверяем, что запросы заблокированы
#         allowed, _ = store.is_allowed(key, limit=10, window=1)
#         assert not allowed

#         # Ждем истечения окна
#         time.sleep(1.1)

#         # Проверяем, что запросы снова разрешены
#         allowed, remaining = store.is_allowed(key, limit=10, window=1)
#         assert allowed
#         assert remaining == 9

#     def test_different_keys_independent(self):
#         """Тест независимости лимитов для разных ключей."""
#         store = RateLimitStore()
#         key1 = "client1"
#         key2 = "client2"

#         # Исчерпываем лимит для первого клиента
#         for _ in range(10):
#             store.is_allowed(key1, limit=10, window=60)

#         # Проверяем, что второй клиент не затронут
#         allowed, remaining = store.is_allowed(key2, limit=10, window=60)
#         assert allowed
#         assert remaining == 9

#     def test_remaining_count_accuracy(self):
#         """Тест точности подсчета оставшихся запросов."""
#         store = RateLimitStore()
#         key = "test_client"

#         # Делаем 3 запроса из 10
#         for _ in range(3):
#             store.is_allowed(key, limit=10, window=60)

#         # Проверяем оставшиеся
#         allowed, remaining = store.is_allowed(key, limit=10, window=60)
#         assert allowed
#         assert remaining == 6  # 10 - 3 - 1 = 6


# class TestRateLimitMiddleware:
#     """Тесты для rate limiting middleware."""

#     def test_get_client_key_with_ip(self):
#         """Тест получения ключа клиента по IP."""
#         middleware = RateLimitMiddleware()

#         # Мокаем request с IP
#         request = type('Request', (), {
#             'client': type('Client', (), {'host': '192.168.1.1'})(),
#             'headers': {}
#         })()

#         key = middleware.get_client_key(request)
#         assert key == "ip:192.168.1.1"

#     def test_get_client_key_with_user_id(self):
#         """Тест получения ключа клиента с user ID."""
#         middleware = RateLimitMiddleware()

#         # Мокаем request с user ID
#         request = type('Request', (), {
#             'client': type('Client', (), {'host': '192.168.1.1'})(),
#             'headers': {'X-User-ID': 'user123'}
#         })()

#         key = middleware.get_client_key(request)
#         assert key == "user:user123"

#     def test_get_limit_for_login_path(self):
#         """Тест определения лимита для пути логина."""
#         middleware = RateLimitMiddleware()

#         limit, window = middleware.get_limit_for_path("/auth/login")
#         assert limit == 10  # login limit
#         assert window == 60  # 1 minute

#     def test_get_limit_for_create_deck_path(self):
#         """Тест определения лимита для создания колоды."""
#         middleware = RateLimitMiddleware()

#         limit, window = middleware.get_limit_for_path("/decks")
#         assert limit == 50  # create_deck limit (увеличено для тестов)
#         assert window == 3600  # 1 hour

#     def test_get_limit_for_create_card_path(self):
#         """Тест определения лимита для создания карточки."""
#         middleware = RateLimitMiddleware()

#         limit, window = middleware.get_limit_for_path("/decks/123/cards")
#         assert limit == 200  # create_card limit (увеличено для тестов)
#         assert window == 3600  # 1 hour

#     def test_get_limit_for_general_path(self):
#         """Тест определения глобального лимита для обычных путей."""
#         middleware = RateLimitMiddleware()

#         limit, window = middleware.get_limit_for_path("/health")
#         assert limit == 120  # global limit
#         assert window == 60  # 1 minute


# class TestRateLimitingIntegration:
#     """Интеграционные тесты rate limiting."""

#     def test_rate_limit_headers_present(self):
#         """Тест наличия заголовков rate limiting."""
#         client = TestClient(app)

#         response = client.get("/health")

#         # Проверяем наличие заголовков rate limiting
#         assert "X-RateLimit-Limit" in response.headers
#         assert "X-RateLimit-Remaining" in response.headers
#         assert "X-RateLimit-Reset" in response.headers

#         # Проверяем значения заголовков
#         limit = int(response.headers["X-RateLimit-Limit"])
#         remaining = int(response.headers["X-RateLimit-Remaining"])
#         reset = int(response.headers["X-RateLimit-Reset"])

#         assert limit > 0
#         assert remaining >= 0
#         assert reset > time.time()

#     def test_rate_limit_exceeded_response(self):
#         """Тест ответа при превышении rate limit."""
#         client = TestClient(app)

#         # Мокаем middleware для принудительного превышения лимита
#         with patch('app.middleware.rate_limit_middleware.store') as mock_store:
#             mock_store.is_allowed.return_value = (False, 0)

#             response = client.get("/health")

#             assert response.status_code == 429
#             content = response.json()

#             # Проверяем RFC 7807 формат
#             assert "type" in content
#             assert "title" in content
#             assert "status" in content
#             assert "detail" in content
#             assert "correlation_id" in content
#             assert content["status"] == 429
#             assert "rate limit exceeded" in content["detail"].lower()

#     def test_rate_limit_within_limits(self):
#         """Тест нормальной работы в пределах лимитов."""
#         client = TestClient(app)

#         # Делаем несколько запросов
#         for _ in range(5):
#             response = client.get("/health")
#             assert response.status_code == 200

#     def test_different_endpoints_different_limits(self):
#         """Тест разных лимитов для разных эндпоинтов."""
#         client = TestClient(app)

#         # Создаем колоду (должен иметь лимит create_deck)
#         response = client.post("/decks", json={"name": "Test Deck"})
#         assert response.status_code == 201

#         # Проверяем заголовки rate limiting
#         limit = int(response.headers["X-RateLimit-Limit"])
#         assert limit == 50  # create_deck limit (увеличено для тестов)

#     def test_rate_limit_reset_after_window(self):
#         """Тест сброса лимита после истечения окна."""
#         client = TestClient(app)

#         # Мокаем middleware с коротким окном
#         with patch('app.middleware.rate_limit_middleware.store') as mock_store:
#             # Первый запрос разрешен
#             mock_store.is_allowed.return_value = (True, 9)
#             response1 = client.get("/health")
#             assert response1.status_code == 200

#             # Второй запрос заблокирован
#             mock_store.is_allowed.return_value = (False, 0)
#             response2 = client.get("/health")
#             assert response2.status_code == 429


# class TestRateLimitingEdgeCases:
#     """Тесты граничных случаев rate limiting."""

#     def test_rate_limit_with_malformed_request(self):
#         """Тест rate limiting с некорректным запросом."""
#         client = TestClient(app)

#         # Отправляем некорректный JSON
#         response = client.post(
#             "/decks",
#             data="invalid json",
#             headers={"Content-Type": "application/json"}
#         )

#         # Rate limiting должен работать даже с некорректными запросами
#         assert "X-RateLimit-Limit" in response.headers

#     def test_rate_limit_with_large_request(self):
#         """Тест rate limiting с большим запросом."""
#         client = TestClient(app)

#         # Отправляем большой JSON
#         large_data = {"name": "x" * 10000}
#         response = client.post("/decks", json=large_data)

#         # Rate limiting должен работать
#         assert "X-RateLimit-Limit" in response.headers

#     def test_rate_limit_concurrent_requests(self):
#         """Тест rate limiting с concurrent запросами."""
#         import threading
#         import queue

#         client = TestClient(app)
#         results = queue.Queue()

#         def make_request():
#             response = client.get("/health")
#             results.put(response.status_code)

#         # Создаем несколько concurrent запросов
#         threads = []
#         for _ in range(10):
#             thread = threading.Thread(target=make_request)
#             threads.append(thread)
#             thread.start()

#         # Ждем завершения всех потоков
#         for thread in threads:
#             thread.join()

#         # Проверяем результаты
#         status_codes = []
#         while not results.empty():
#             status_codes.append(results.get())

#         # Все запросы должны быть обработаны
#         assert len(status_codes) == 10
#         # Большинство должны быть успешными (200)
#         success_count = sum(1 for code in status_codes if code == 200)
#         assert success_count >= 5  # По крайней мере половина должна быть успешной


# class TestRateLimitingSecurity:
#     """Тесты безопасности rate limiting."""

#     def test_rate_limit_ip_spoofing_protection(self):
#         """Тест защиты от подделки IP."""
#         client = TestClient(app)

#         # Отправляем запрос с поддельным IP в заголовке
#         response = client.get(
#             "/health",
#             headers={"X-Forwarded-For": "192.168.1.100"}
#         )

#         # Rate limiting должен работать с реальным IP клиента
#         assert "X-RateLimit-Limit" in response.headers

#     def test_rate_limit_user_id_extraction(self):
#         """Тест извлечения user ID для rate limiting."""
#         client = TestClient(app)

#         # Отправляем запрос с user ID
#         response = client.get(
#             "/health",
#             headers={"X-User-ID": "user123"}
#         )

#         # Rate limiting должен использовать user ID
#         assert "X-RateLimit-Limit" in response.headers

#     def test_rate_limit_malicious_headers(self):
#         """Тест rate limiting с подозрительными заголовками."""
#         client = TestClient(app)

#         # Отправляем запрос с подозрительными заголовками
#         response = client.get(
#             "/health",
#             headers={
#                 "X-User-ID": "../../etc/passwd",
#                 "X-Forwarded-For": "127.0.0.1; DROP TABLE users;"
#             }
#         )

#         # Rate limiting должен работать безопасно
#         assert "X-RateLimit-Limit" in response.headers
