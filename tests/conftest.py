# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Отключаем rate limiting для всех тестов
os.environ["DISABLE_RATE_LIMITING"] = "1"
# Используем in-memory БД для тестов
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Отключаем автоматический init_db при импорте app
os.environ["TESTING"] = "1"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import database, models  # noqa: E402, F401
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = "sqlite:///:memory:"
# Используем StaticPool чтобы все connections использовали одну и ту же in-memory БД
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Переопределяем глобальные переменные в database модуле
database.engine = test_engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="function")
def db_session():
    """Создаёт чистую БД для каждого теста."""
    # Создаём таблицы
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

    # Удаляем таблицы после теста
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient с подменой БД на тестовую."""

    def override_get_db():
        """Переопределение get_db для использования тестовой сессии."""
        try:
            yield db_session
        finally:
            pass

    # Переопределяем dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Очищаем переопределение
    app.dependency_overrides.clear()
