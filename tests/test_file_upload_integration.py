"""
Интеграционные тесты для загрузки файлов (ADR-001).
Тестирует полный цикл загрузки файлов через API.
"""

import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class TestFileUploadIntegration:
    """Интеграционные тесты загрузки файлов."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.client = TestClient(app)
        self.upload_dir = "uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    def teardown_method(self):
        """Очистка после каждого теста."""
        # Очищаем загруженные файлы
        if os.path.exists(self.upload_dir):
            for file in Path(self.upload_dir).glob("*"):
                if file.is_file():
                    file.unlink()

    def test_upload_valid_png_image(self):
        """Тест загрузки валидного PNG изображения."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        assert deck_response.status_code == 201
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        assert card_response.status_code == 201
        card_id = card_response.json()["id"]

        # Создаем валидный PNG файл
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        # Загружаем изображение
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("test.png", png_data, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "image_path" in data
        assert "card_id" in data
        assert data["card_id"] == card_id

        # Проверяем, что файл действительно сохранен
        image_path = data["image_path"]
        assert Path(image_path).exists()
        assert Path(image_path).read_bytes() == png_data

    def test_upload_valid_jpeg_image(self):
        """Тест загрузки валидного JPEG изображения."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        # Создаем валидный JPEG файл
        jpeg_data = b"\xff\xd8" + b"fake_jpeg_data" + b"\xff\xd9"

        # Загружаем изображение
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["image_path"].endswith(".jpg")

    def test_upload_invalid_file_type(self):
        """Тест загрузки файла недопустимого типа."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        # Создаем невалидный файл
        invalid_data = b"not_an_image"

        # Пытаемся загрузить невалидный файл
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("test.txt", invalid_data, "text/plain")},
        )

        assert response.status_code == 422
        data = response.json()

        # Проверяем RFC 7807 формат ошибки
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "correlation_id" in data
        assert data["status"] == 422
        assert "not allowed" in data["detail"]

    def test_upload_file_too_large(self):
        """Тест загрузки файла превышающего лимит размера."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        # Создаем файл превышающий лимит (5MB + 1 байт)
        large_data = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024 + 1)

        # Пытаемся загрузить большой файл
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("large.png", large_data, "image/png")},
        )

        assert response.status_code == 422
        data = response.json()
        assert "exceeds limit" in data["detail"]

    def test_upload_to_nonexistent_deck(self):
        """Тест загрузки в несуществующую колоду."""
        fake_deck_id = str(uuid.uuid4())
        fake_card_id = str(uuid.uuid4())

        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        response = self.client.post(
            f"/decks/{fake_deck_id}/cards/{fake_card_id}/image",
            files={"file": ("test.png", png_data, "image/png")},
        )

        assert response.status_code == 404
        data = response.json()
        assert "deck" in data["detail"]
        assert fake_deck_id in data["detail"]

    def test_upload_to_nonexistent_card(self):
        """Тест загрузки для несуществующей карточки."""
        # Создаем тестовую колоду
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        fake_card_id = str(uuid.uuid4())
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        response = self.client.post(
            f"/decks/{deck_id}/cards/{fake_card_id}/image",
            files={"file": ("test.png", png_data, "image/png")},
        )

        assert response.status_code == 404
        data = response.json()
        assert "card" in data["detail"]
        assert fake_card_id in data["detail"]

    def test_upload_wrong_card_for_deck(self):
        """Тест загрузки для карточки из другой колоды."""
        # Создаем две колоды
        deck1_response = self.client.post("/decks", json={"name": "Deck 1"})
        deck1_id = deck1_response.json()["id"]

        deck2_response = self.client.post("/decks", json={"name": "Deck 2"})
        deck2_id = deck2_response.json()["id"]

        # Создаем карточку в первой колоде
        card_response = self.client.post(
            f"/decks/{deck1_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        # Пытаемся загрузить изображение для карточки из другой колоды
        response = self.client.post(
            f"/decks/{deck2_id}/cards/{card_id}/image",
            files={"file": ("test.png", png_data, "image/png")},
        )

        assert response.status_code == 404
        data = response.json()
        assert "card" in data["detail"]

    def test_upload_with_malicious_filename(self):
        """Тест загрузки с подозрительным именем файла."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        # Пытаемся загрузить с подозрительным именем
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("../../../etc/passwd", png_data, "image/png")},
        )

        # Должно быть отклонено из-за подозрительного имени
        assert response.status_code == 422
        data = response.json()
        assert "invalid characters" in data["detail"]

    def test_upload_multiple_images_same_card(self):
        """Тест загрузки нескольких изображений для одной карточки."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        # Загружаем первое изображение
        response1 = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("test1.png", png_data, "image/png")},
        )
        assert response1.status_code == 200

        # Загружаем второе изображение (должно заменить первое)
        response2 = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("test2.png", png_data, "image/png")},
        )
        assert response2.status_code == 200

        # Проверяем, что пути разные (UUID имена)
        path1 = response1.json()["image_path"]
        path2 = response2.json()["image_path"]
        assert path1 != path2

    def test_upload_with_empty_file(self):
        """Тест загрузки пустого файла."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        # Пытаемся загрузить пустой файл
        response = self.client.post(
            f"/decks/{deck_id}/cards/{card_id}/image",
            files={"file": ("empty.png", b"", "image/png")},
        )

        assert response.status_code == 422
        data = response.json()
        assert "not allowed" in data["detail"]

    def test_upload_without_file_parameter(self):
        """Тест загрузки без параметра файла."""
        # Создаем тестовую колоду и карточку
        deck_response = self.client.post("/decks", json={"name": "Test Deck"})
        deck_id = deck_response.json()["id"]

        card_response = self.client.post(
            f"/decks/{deck_id}/cards", json={"front": "Test", "back": "Answer"}
        )
        card_id = card_response.json()["id"]

        # Пытаемся загрузить без файла
        response = self.client.post(f"/decks/{deck_id}/cards/{card_id}/image")

        assert response.status_code == 422  # FastAPI validation error
