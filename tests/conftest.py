# tests/conftest.py
import os
import sys
from pathlib import Path

# Отключаем rate limiting для всех тестов
os.environ["DISABLE_RATE_LIMITING"] = "1"

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
