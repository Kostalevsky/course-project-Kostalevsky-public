import uuid
from pathlib import Path
from typing import Tuple

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def sniff_image_type(data: bytes) -> str | None:
    if data.startswith(PNG_SIGNATURE):
        return "image/png"
    if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
        return "image/jpeg"
    return None


def secure_save(base_dir: str, filename_hint: str, data: bytes) -> Tuple[bool, str]:
    if len(data) > MAX_FILE_SIZE:
        return False, "file_too_large"

    mime_type = sniff_image_type(data)
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, "invalid_file_type"

    try:
        root = Path(base_dir).resolve(strict=True)
    except (OSError, FileNotFoundError):
        return False, "invalid_base_directory"

    if mime_type == "image/png":
        extension = ".png"
    else:
        extension = ".jpg"

    safe_filename = f"{uuid.uuid4()}{extension}"
    file_path = (root / safe_filename).resolve()

    if not str(file_path).startswith(str(root)):
        return False, "path_traversal_detected"

    try:
        for parent in file_path.parents:
            if parent.is_symlink():
                return False, "symlink_in_path"
    except OSError:
        return False, "path_validation_error"

    try:
        with open(file_path, "wb") as f:
            f.write(data)
        return True, str(file_path)
    except OSError as e:
        return False, f"save_error: {str(e)}"


def validate_file_upload(data: bytes, filename: str) -> Tuple[bool, str]:
    if len(data) > MAX_FILE_SIZE:
        return False, f"File size exceeds limit of {MAX_FILE_SIZE} bytes"

    mime_type = sniff_image_type(data)
    if mime_type not in ALLOWED_MIME_TYPES:
        return (
            False,
            f"File type {mime_type} not allowed. Only PNG and JPEG are supported",
        )

    if any(char in filename for char in ["..", "/", "\\", "\x00"]):
        return False, "Filename contains invalid characters"

    return True, "File is valid"
