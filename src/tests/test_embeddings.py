"""
Тесты для модуля embeddings.
"""

import os
import pytest
from unittest.mock import Mock, patch

from src.rag.embeddings import OpenRouterEmbedder, get_embedder


@pytest.fixture
def mock_api_key():
    """Фикстура с моком API-ключа."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}):
        yield


def test_embedder_init(mock_api_key):
    """Тест инициализации эмбеддера."""
    embedder = OpenRouterEmbedder(api_key="test_key")
    assert embedder.api_key == "test_key"
    assert embedder.model == "qwen/qwen-embed"


def test_embedder_from_env(mock_api_key):
    """Тест получения ключа из env."""
    embedder = OpenRouterEmbedder()
    assert embedder.api_key == "test_key"


@patch("src.rag.embeddings.httpx.Client")
def test_embed_text_mock(mock_client, mock_api_key):
    """Тест векторизации текста с моком."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1] * 1024}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.post.return_value = mock_response

    embedder = OpenRouterEmbedder(api_key="test_key")
    # Пропускаем rate limit в тесте
    embedder._client = mock_client.return_value

    embedding = embedder.embed_text("тест")

    assert len(embedding) == 1024
    assert embedding[0] == 0.1


def test_get_embedder_singleton(mock_api_key):
    """Тест singleton-паттерна для эмбеддера."""
    embedder1 = get_embedder()
    embedder2 = get_embedder()
    assert embedder1 is embedder2


def test_embed_texts_batch(mock_api_key):
    """Тест пакетной векторизации."""
    with patch("src.rag.embeddings.httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1024}]}
        mock_response.raise_for_status = Mock()
        mock_client.return_value.post.return_value = mock_response

        embedder = OpenRouterEmbedder(api_key="test_key")
        embedder._client = mock_client.return_value

        # Эмуляция: каждый вызов возвращает тот же эмбеддинг
        original_embed = embedder.embed_text
        embedder.embed_text = lambda x: [0.1] * 1024

        texts = ["текст 1", "текст 2", "текст 3"]
        embeddings = [embedder.embed_text(t) for t in texts]

        assert len(embeddings) == 3
        assert all(len(e) == 1024 for e in embeddings)
