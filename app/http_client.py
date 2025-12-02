import time

import httpx

SAFE_TIMEOUT = httpx.Timeout(5.0, read=5.0, connect=3.0)


def safe_get(
    url: str, *, attempts: int = 3, timeout: httpx.Timeout | None = None
) -> httpx.Response:
    t = timeout or SAFE_TIMEOUT
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            with httpx.Client(
                timeout=t,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            ) as c:
                r = c.get(url, follow_redirects=True)
                r.raise_for_status()
                return r
        except Exception as exc:
            last_exc = exc
            if i == attempts - 1:
                raise
            time.sleep(0.5 * (i + 1))
    assert last_exc is not None
    raise last_exc
