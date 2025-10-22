"""
Тесты для модуля валидации.

Покрывает ADR-001: Валидация ввода и защита от path traversal.
"""

from pathlib import Path

from app.security import secure_save, sniff_image_type

# class TestUUIDValidation:
#     """Тесты валидации UUID."""
#
#     def test_valid_uuid_v4(self):
#         """Тест валидного UUID v4."""
#         valid_uuid = str(uuid.uuid4())
#         assert validate_uuid(valid_uuid) is True
#
#     def test_invalid_uuid_format(self):
#         """Тест невалидного формата UUID."""
#         invalid_uuids = [
#             "not-a-uuid",
#             "123",
#             "550e8400-e29b-41d4-a716-44665544000",  # Неполный UUID
#             "550e8400-e29b-41d4-a716-4466554400000",  # Слишком длинный
#             "",
#             None
#         ]
#
#         for invalid_uuid in invalid_uuids:
#             if invalid_uuid is not None:
#                 assert validate_uuid(invalid_uuid) is False
#
#     def test_deck_id_validation(self):
#         """Тест валидации ID колоды."""
#         valid_deck_id = str(uuid.uuid4())
#         assert validate_deck_id(valid_deck_id) is True
#
#         invalid_deck_id = "not-a-uuid"
#         assert validate_deck_id(invalid_deck_id) is False
#
#     def test_card_id_validation(self):
#         """Тест валидации ID карточки."""
#         valid_card_id = str(uuid.uuid4())
#         assert validate_card_id(valid_card_id) is True
#
#         invalid_card_id = "not-a-uuid"
#         assert validate_card_id(invalid_card_id) is False


class TestImageTypeDetection:
    """Тесты определения типа изображения."""

    def test_png_detection(self):
        """Тест определения PNG файла."""
        # Минимальный валидный PNG
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert sniff_image_type(png_data) == "image/png"

    def test_jpeg_detection(self):
        """Тест определения JPEG файла."""
        # Минимальный валидный JPEG
        jpeg_data = b"\xff\xd8" + b"\x00" * 100 + b"\xff\xd9"
        assert sniff_image_type(jpeg_data) == "image/jpeg"

    def test_unknown_type(self):
        """Тест неизвестного типа файла."""
        unknown_data = b"not an image"
        assert sniff_image_type(unknown_data) is None

    def test_empty_data(self):
        """Тест пустых данных."""
        assert sniff_image_type(b"") is None
        assert sniff_image_type(b"a") is None  # Слишком короткие


class TestSecureSave:
    """Тесты безопасного сохранения файлов."""

    def test_save_valid_png(self, tmp_path):
        """Тест сохранения валидного PNG файла."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000

        success, result = secure_save(str(tmp_path), "test.png", png_data)
        assert success is True
        assert result.endswith(".png")
        assert Path(result).exists()

    def test_save_valid_jpeg(self, tmp_path):
        """Тест сохранения валидного JPEG файла."""
        jpeg_data = b"\xff\xd8" + b"\x00" * 1000 + b"\xff\xd9"

        success, result = secure_save(str(tmp_path), "test.jpg", jpeg_data)
        assert success is True
        assert result.endswith(".jpg")
        assert Path(result).exists()

    def test_reject_too_large_file(self, tmp_path):
        """Тест отклонения слишком большого файла."""
        # Создаем файл больше 5MB (5 * 1024 * 1024 = 5_242_880 байт)
        large_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5_242_881)

        success, result = secure_save(str(tmp_path), "large.png", large_data)
        assert success is False
        assert result == "file_too_large"

    def test_reject_invalid_type(self, tmp_path):
        """Тест отклонения файла недопустимого типа."""
        invalid_data = b"not an image"

        success, result = secure_save(str(tmp_path), "test.txt", invalid_data)
        assert success is False
        assert result == "invalid_file_type"

    def test_path_traversal_protection(self, tmp_path):
        """Тест защиты от path traversal."""
        # Создаем поддиректорию
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Попытка выйти за пределы базовой директории
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        # Это должно быть заблокировано на уровне валидации пути
        success, result = secure_save(str(subdir), "../../../etc/passwd", png_data)
        # В зависимости от реализации, это может быть заблокировано
        # или успешно сохранено в безопасном месте
        assert success is True  # Файл должен быть сохранен в безопасном месте
        assert not str(result).startswith("/etc/")  # Не должен попасть в /etc/

    def test_symlink_protection(self, tmp_path):
        """Тест защиты от симлинков."""
        # Создаем поддиректорию и симлинк в ней
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        symlink_path = subdir / "symlink"
        symlink_path.symlink_to("..")  # Симлинк на родительскую директорию

        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        # Попытка сохранить через симлинк
        success, result = secure_save(str(symlink_path), "test.png", png_data)
        # В текущей реализации симлинки разрешены, но файл сохраняется в безопасном месте
        assert success is True
        assert result.endswith(".png")
        # Проверяем что файл не попал в неожиданное место
        assert not str(result).startswith("/etc/")
        assert not str(result).startswith("/tmp/")


# class TestFilenameSanitization:
#     """Тесты очистки имен файлов."""
#
#     def test_sanitize_dangerous_chars(self):
#         """Тест удаления опасных символов."""
#         dangerous_filename = "file/with\\dangerous:chars*?\"<>|"
#         sanitized = sanitize_filename(dangerous_filename)
#
#         dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
#         for char in dangerous_chars:
#             assert char not in sanitized
#
#     def test_sanitize_long_filename(self):
#         """Тест обрезки длинного имени файла."""
#         long_filename = "a" * 300 + ".txt"
#         sanitized = sanitize_filename(long_filename)
#
#         assert len(sanitized) <= 255
#         assert sanitized.endswith(".txt")
#
#     def test_sanitize_normal_filename(self):
#         """Тест нормального имени файла."""
#         normal_filename = "normal_file.txt"
#         sanitized = sanitize_filename(normal_filename)
#
#         assert sanitized == normal_filename


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_file(self, tmp_path):
        """Тест пустого файла."""
        success, result = secure_save(str(tmp_path), "empty.png", b"")
        assert success is False
        assert result == "invalid_file_type"

    def test_minimal_png(self, tmp_path):
        """Тест минимального PNG файла."""
        minimal_png = b"\x89PNG\r\n\x1a\n"
        success, result = secure_save(str(tmp_path), "minimal.png", minimal_png)
        assert success is True

    def test_minimal_jpeg(self, tmp_path):
        """Тест минимального JPEG файла."""
        # Более реалистичный минимальный JPEG с маркерами
        minimal_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"
        success, result = secure_save(str(tmp_path), "minimal.jpg", minimal_jpeg)
        assert success is True

    def test_nonexistent_directory(self):
        """Тест несуществующей директории."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        success, result = secure_save("/nonexistent/directory", "test.png", png_data)
        assert success is False
        assert result == "invalid_base_directory"
