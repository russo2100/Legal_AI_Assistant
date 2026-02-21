"""
Тесты для API сервера Dashboard.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Добавляем корень проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.server import app

client = TestClient(app)


def test_health_check():
    """Тест проверки здоровья сервера."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_root_endpoint():
    """Тест корневого endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert "health" in data


def test_search_empty_query():
    """Тест поиска с пустым запросом."""
    response = client.post("/api/search", json={"query": ""})
    assert response.status_code == 422  # Validation error


def test_search_with_results():
    """Тест поиска с запросом."""
    response = client.post("/api/search", json={"query": "Статья 330"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_search_norm_query():
    """Тест поиска нормативных актов."""
    response = client.post("/api/search", json={"query": "ГК РФ неустойка"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
    
    # Проверяем структуру результатов
    for result in data["results"]:
        assert "id" in result
        assert "title" in result
        assert "type" in result
        assert result["type"] in ["norm", "case"]


def test_search_case_query():
    """Тест поиска судебных дел."""
    response = client.post("/api/search", json={"query": "Дело А40"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
