from pathlib import Path

from app.security import MAX_FILE_SIZE, secure_save, sniff_image_type, validate_file_upload


class TestSniffImageType:

    def test_sniff_png(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        assert sniff_image_type(png_data) == "image/png"

    def test_sniff_jpeg(self):
        jpeg_data = b"\xff\xd8" + b"fake_jpeg_data" + b"\xff\xd9"
        assert sniff_image_type(jpeg_data) == "image/jpeg"

    def test_sniff_invalid_type(self):
        invalid_data = b"not_an_image"
        assert sniff_image_type(invalid_data) is None

    def test_sniff_empty_data(self):
        assert sniff_image_type(b"") is None

    def test_sniff_partial_jpeg(self):
        partial_jpeg = b"\xff\xd8" + b"fake_data"
        assert sniff_image_type(partial_jpeg) is None


class TestValidateFileUpload:
    def test_validate_valid_png(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        is_valid, msg = validate_file_upload(png_data, "test.png")
        assert is_valid
        assert msg == "File is valid"

    def test_validate_valid_jpeg(self):
        jpeg_data = b"\xff\xd8" + b"fake_jpeg_data" + b"\xff\xd9"
        is_valid, msg = validate_file_upload(jpeg_data, "test.jpg")
        assert is_valid
        assert msg == "File is valid"

    def test_validate_file_too_large(self):
        large_data = b"\x89PNG\r\n\x1a\n" + b"x" * (MAX_FILE_SIZE + 1)
        is_valid, msg = validate_file_upload(large_data, "large.png")
        assert not is_valid
        assert "exceeds limit" in msg

    def test_validate_invalid_type(self):
        invalid_data = b"not_an_image"
        is_valid, msg = validate_file_upload(invalid_data, "test.txt")
        assert not is_valid
        assert "not allowed" in msg

    def test_validate_suspicious_filename(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        is_valid, msg = validate_file_upload(png_data, "../../../etc/passwd")
        assert not is_valid
        assert "invalid characters" in msg

    def test_validate_null_byte_filename(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        is_valid, msg = validate_file_upload(png_data, "test\x00.png")
        assert not is_valid
        assert "invalid characters" in msg


class TestSecureSave:
    def test_secure_save_valid_png(self, tmp_path):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        success, result = secure_save(str(tmp_path), "test.png", png_data)

        assert success
        assert result.endswith(".png")
        assert Path(result).exists()
        assert Path(result).read_bytes() == png_data

    def test_secure_save_valid_jpeg(self, tmp_path):
        jpeg_data = b"\xff\xd8" + b"fake_jpeg_data" + b"\xff\xd9"
        success, result = secure_save(str(tmp_path), "test.jpg", jpeg_data)

        assert success
        assert result.endswith(".jpg")
        assert Path(result).exists()
        assert Path(result).read_bytes() == jpeg_data

    def test_secure_save_file_too_large(self, tmp_path):
        large_data = b"\x89PNG\r\n\x1a\n" + b"x" * (MAX_FILE_SIZE + 1)
        success, result = secure_save(str(tmp_path), "large.png", large_data)

        assert not success
        assert result == "file_too_large"

    def test_secure_save_invalid_type(self, tmp_path):
        invalid_data = b"not_an_image"
        success, result = secure_save(str(tmp_path), "test.txt", invalid_data)

        assert not success
        assert result == "invalid_file_type"

    def test_secure_save_nonexistent_directory(self):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        success, result = secure_save("/nonexistent/path", "test.png", png_data)

        assert not success
        assert result == "invalid_base_directory"

    def test_secure_save_path_traversal_attempt(self, tmp_path):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        success, result = secure_save(str(tmp_path), "../../../etc/passwd", png_data)

        assert success
        assert not result.endswith("passwd")
        assert Path(result).exists()

    def test_secure_save_generates_uuid_filename(self, tmp_path):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        success, result = secure_save(str(tmp_path), "original.png", png_data)

        assert success
        filename = Path(result).name
        assert len(filename) == 36 + 4  # UUID + .png
        assert filename.endswith(".png")
        assert filename.count("-") == 4  # UUID формат

    def test_secure_save_multiple_files_unique_names(self, tmp_path):
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"

        success1, result1 = secure_save(str(tmp_path), "test1.png", png_data)
        success2, result2 = secure_save(str(tmp_path), "test2.png", png_data)

        assert success1 and success2
        assert result1 != result2
        assert Path(result1).exists()
        assert Path(result2).exists()


class TestSecurityEdgeCases:

    def test_empty_file_validation(self):
        is_valid, msg = validate_file_upload(b"", "empty.png")
        assert not is_valid
        assert "not allowed" in msg

    def test_minimal_valid_png(self):
        minimal_png = b"\x89PNG\r\n\x1a\n"
        is_valid, msg = validate_file_upload(minimal_png, "minimal.png")
        assert is_valid

    def test_minimal_valid_jpeg(self):
        minimal_jpeg = b"\xff\xd8\xff\xd9"
        is_valid, msg = validate_file_upload(minimal_jpeg, "minimal.jpg")
        assert is_valid

    def test_file_size_exactly_at_limit(self, tmp_path):
        png_header = b"\x89PNG\r\n\x1a\n"
        padding = b"x" * (MAX_FILE_SIZE - len(png_header))
        data = png_header + padding

        success, result = secure_save(str(tmp_path), "exact_size.png", data)
        assert success
        assert Path(result).exists()

    def test_file_size_one_byte_over_limit(self, tmp_path):
        png_header = b"\x89PNG\r\n\x1a\n"
        padding = b"x" * (MAX_FILE_SIZE - len(png_header) + 1)
        data = png_header + padding

        success, result = secure_save(str(tmp_path), "too_large.png", data)
        assert not success
        assert result == "file_too_large"
