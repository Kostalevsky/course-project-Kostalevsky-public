# syntax=docker/dockerfile:1.7-labs


FROM python:3.11.10-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip && \
    pip wheel --wheel-dir=/wheels -r requirements.txt

COPY app ./app
# COPY requirements-dev.txt .
# RUN --mount=type=cache,target=/root/.cache pip install -r requirements-dev.txt && pytest -q


FROM python:3.11.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -g 10001 app && useradd -u 10001 -g 10001 -m -s /usr/sbin/nologin app

WORKDIR /app

COPY --from=build /wheels /wheels
RUN --mount=type=cache,target=/root/.cache \
    pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY --chown=10001:10001 app ./app

RUN mkdir -p /data && chown -R 10001:10001 /data
ENV DATABASE_URL=sqlite:////data/flashcards.db

USER 10001:10001

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import sys, json, urllib.request; \
try: \
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2); \
    ok = (r.status == 200) and (json.loads(r.read()).get('status') == 'ok'); \
    sys.exit(0 if ok else 1) \
except Exception: \
    sys.exit(1)"

EXPOSE 8000

ENTRYPOINT ["python","-m","uvicorn","app.main:app"]
CMD ["--host","0.0.0.0","--port","8000","--workers","2"]
