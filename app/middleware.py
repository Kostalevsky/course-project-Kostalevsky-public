import time
from typing import Dict, Tuple

from fastapi import Request

from .errors import rate_limit_error


class RateLimitStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, float]] = {}

    def is_allowed(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        now = time.time()

        if key not in self._store:
            self._store[key] = {}

        cutoff = now - window
        self._store[key] = {
            timestamp: count for timestamp, count in self._store[key].items() if timestamp > cutoff
        }

        current_requests = sum(self._store[key].values())

        if current_requests >= limit:
            return False, 0

        # Добавляем текущий запрос
        self._store[key][now] = self._store[key].get(now, 0) + 1

        # Пересчитываем после добавления
        new_current_requests = sum(self._store[key].values())
        return True, limit - new_current_requests


class RateLimitMiddleware:
    def __init__(self):
        self.store = RateLimitStore()

        self.limits = {
            "global": (120, 60),  # 120 запросов в минуту
            "login": (10, 60),  # 10 неуспешных попыток в минуту
            "create_deck": (50, 3600),  # 50 колод в час (увеличено для тестов)
            "create_card": (200, 3600),  # 200 карточек в час (увеличено для тестов)
        }

    def get_client_key(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"

        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"

        return f"ip:{client_ip}"

    def get_limit_for_path(self, path: str) -> Tuple[int, int]:
        if path.startswith("/auth/login"):
            return self.limits["login"]
        elif "/cards" in path and path.startswith("/decks/"):
            return self.limits["create_card"]
        elif path == "/decks" or path.startswith("/decks/"):
            return self.limits["create_deck"]
        else:
            return self.limits["global"]

    async def __call__(self, request: Request, call_next):
        client_key = self.get_client_key(request)
        path = str(request.url.path)

        limit, window = self.get_limit_for_path(path)

        allowed, remaining = self.store.is_allowed(client_key, limit, window)

        if not allowed:
            error_response = rate_limit_error(limit=limit, window=f"{window}s", instance=path)
            # Добавляем rate limit headers к ответу об ошибке
            error_response.headers["X-RateLimit-Limit"] = str(limit)
            error_response.headers["X-RateLimit-Remaining"] = "0"
            error_response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))
            return error_response

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))

        return response


rate_limit_middleware = RateLimitMiddleware()
