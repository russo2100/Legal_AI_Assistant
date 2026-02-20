"""
Конфигурация pytest и общие фикстуры.
"""

import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def setup_env():
    """Фикстура для настройки тестового окружения."""
    # Устанавлием тестовые переменные окружения
    os.environ.setdefault("OPENROUTER_API_KEY", "test_key")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    yield
    # Очистка после теста (если нужно)


@pytest.fixture
def project_root():
    """Возвращает корень проекта."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def tests_dir():
    """Возвращает директорию с тестами."""
    return Path(__file__).parent


@pytest.fixture
def golden_set_path(tests_dir):
    """Путь к golden set."""
    return tests_dir / "golden_set.jsonl"
