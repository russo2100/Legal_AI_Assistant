"""
Тесты для LLM-клиента с fallback-логикой.

Проверяют:
1. Работу основного провайдера (OpenRouter)
2. Переключение на fallback (Perplexity) при ошибке
3. Обработку ситуации когда оба провайдера недоступны
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from src.llm.client import (
    OpenRouterClient,
    MultiLLMClient,
    LLMResponse,
)
from src.llm.perplexity_client import PerplexityClient, PerplexityResponse


class TestOpenRouterClient:
    """Тесты для OpenRouter клиента."""

    def test_init_with_env_vars(self):
        """Тест инициализации с переменными окружения."""
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "OPENROUTER_MODEL": "test-model",
            },
        ):
            client = OpenRouterClient()
            assert client.api_key == "test-key"
            assert client.model == "test-model"

    def test_init_without_api_key(self, caplog):
        """Тест инициализации без API-ключа."""
        with patch.dict(os.environ, {}, clear=True):
            client = OpenRouterClient()
            assert client.api_key == ""
            assert "OPENROUTER_API_KEY не установлен" in caplog.text

    def test_generate_success(self):
        """Тест успешного запроса."""
        client = OpenRouterClient(api_key="test-key")
        
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Test response"},
                    "finish_reason": "stop",
                }
            ],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            response = client.generate("Test prompt")
            
            assert response.content == "Test response"
            assert response.model == "test-model"
            assert response.provider == "openrouter"
            assert response.usage["total_tokens"] == 30

    def test_generate_with_system_prompt(self):
        """Тест запроса с системным промптом."""
        client = OpenRouterClient(api_key="test-key")
        
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Response with system prompt"},
                    "finish_reason": "stop",
                }
            ],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        with patch.object(client, "_make_request", return_value=mock_response) as mock_request:
            response = client.generate("Test prompt", system_prompt="You are helpful")
            
            # Проверяем что системный промпт был передан
            call_args = mock_request.call_args[0][0]
            assert len(call_args) == 2
            assert call_args[0]["role"] == "system"
            assert call_args[1]["role"] == "user"


class TestPerplexityClient:
    """Тесты для Perplexity клиента."""

    def test_init_with_env_vars(self):
        """Тест инициализации с переменными окружения."""
        with patch.dict(
            os.environ,
            {
                "PERPLEXITY_API_KEY": "test-key",
                "PERPLEXITY_MODEL": "sonar-large-online",
            },
        ):
            client = PerplexityClient()
            assert client.api_key == "test-key"
            assert client.model == "sonar-large-online"

    def test_init_without_api_key(self, caplog):
        """Тест инициализации без API-ключа."""
        with patch.dict(os.environ, {}, clear=True):
            client = PerplexityClient()
            assert client.api_key == ""
            assert "PERPLEXITY_API_KEY не установлен" in caplog.text

    def test_generate_success(self):
        """Тест успешного запроса."""
        client = PerplexityClient(api_key="test-key")
        
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Perplexity response"},
                    "finish_reason": "stop",
                }
            ],
            "model": "sonar-large-online",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            response = client.generate("Test prompt")
            
            assert response.content == "Perplexity response"
            assert response.model == "sonar-large-online"
            assert response.usage["total_tokens"] == 30


class TestMultiLLMClient:
    """Тесты для MultiLLM клиента с fallback-логикой."""

    def test_init(self):
        """Тест инициализации MultiLLM клиента."""
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "PERPLEXITY_API_KEY": "test-fallback-key",
            },
            clear=True,
        ):
            client = MultiLLMClient()
            assert client.primary_client is not None
            assert client.fallback_client is not None

    def test_generate_primary_success(self):
        """Тест успешного запроса к основному провайдеру."""
        client = MultiLLMClient()
        
        mock_response = LLMResponse(
            content="Primary response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
            provider="openrouter",
        )

        with patch.object(client.primary_client, "generate", return_value=mock_response):
            response = client.generate("Test prompt")
            
            assert response.content == "Primary response"
            assert response.provider == "openrouter"

    def test_generate_fallback_on_primary_failure(self):
        """Тест переключения на fallback при ошибке основного."""
        client = MultiLLMClient()
        
        # Основной провайдер выбрасывает ошибку
        with patch.object(
            client.primary_client,
            "generate",
            side_effect=Exception("OpenRouter unavailable"),
        ):
            # Fallback провайдер возвращает успешный ответ
            mock_fallback_response = PerplexityResponse(
                content="Fallback response",
                model="sonar-large-online",
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                finish_reason="stop",
            )
            
            with patch.object(client.fallback_client, "generate", return_value=mock_fallback_response):
                response = client.generate("Test prompt")
                
                assert response.content == "Fallback response"
                assert response.provider == "perplexity"

    def test_generate_all_providers_fail(self):
        """Тест ошибки когда все провайдеры недоступны."""
        client = MultiLLMClient()
        
        # Оба провайдера выбрасывают ошибку
        with patch.object(
            client.primary_client,
            "generate",
            side_effect=Exception("OpenRouter unavailable"),
        ):
            with patch.object(
                client.fallback_client,
                "generate",
                side_effect=Exception("Perplexity unavailable"),
            ):
                with pytest.raises(RuntimeError, match="Все LLM-провайдеры недоступны"):
                    client.generate("Test prompt")

    def test_generate_json_success(self):
        """Тест успешной генерации JSON."""
        client = MultiLLMClient()
        
        mock_response = LLMResponse(
            content='{"key": "value"}',
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
            provider="openrouter",
        )

        with patch.object(client.primary_client, "generate", return_value=mock_response):
            result = client.generate_json("Test prompt")
            
            assert result == {"key": "value"}

    def test_generate_json_with_markdown(self):
        """Тест генерации JSON с markdown-блоками."""
        client = MultiLLMClient()
        
        mock_response = LLMResponse(
            content='```json\n{"key": "value"}\n```',
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
            provider="openrouter",
        )

        with patch.object(client.primary_client, "generate", return_value=mock_response):
            result = client.generate_json("Test prompt")
            
            assert result == {"key": "value"}

    def test_generate_json_invalid(self, caplog):
        """Тест генерации с невалидным JSON."""
        client = MultiLLMClient()
        
        mock_response = LLMResponse(
            content="This is not JSON",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
            provider="openrouter",
        )

        with patch.object(client.primary_client, "generate", return_value=mock_response):
            result = client.generate_json("Test prompt")
            
            assert "error" in result
            assert "Failed to parse JSON response" in result["error"]


class TestFallbackIntegration:
    """Интеграционные тесты fallback-логики."""

    def test_fallback_logging(self, caplog):
        """Тест логирования при переключении на fallback."""
        # Устанавливаем API ключи для тестов (сохраняем PATH)
        env = os.environ.copy()
        env["OPENROUTER_API_KEY"] = "test-key"
        env["PERPLEXITY_API_KEY"] = "test-fallback-key"
        
        with patch.dict(os.environ, env, clear=False):
            client = MultiLLMClient()
            
            with patch.object(
                client.primary_client,
                "generate",
                side_effect=Exception("OpenRouter error"),
            ):
                mock_fallback_response = PerplexityResponse(
                    content="Fallback response",
                    model="sonar-large-online",
                    usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                    finish_reason="stop",
                )
                
                with patch.object(client.fallback_client, "generate", return_value=mock_fallback_response):
                    result = client.generate("Test prompt")
                    
                    # Проверяем что было залогировано предупреждение об ошибке OpenRouter
                    assert "OpenRouter недоступен" in caplog.text
                    # Проверяем что ответ получен от fallback провайдера
                    assert result.provider == "perplexity"
                    assert result.content == "Fallback response"

    def test_use_fallback_flag(self):
        """Тест флага use_fallback=False."""
        client = MultiLLMClient()
        
        with patch.object(
            client.primary_client,
            "generate",
            side_effect=Exception("OpenRouter error"),
        ):
            # use_fallback=False должен выбрасывать ошибку сразу
            with pytest.raises(Exception, match="OpenRouter error"):
                client.generate("Test prompt", use_fallback=False)
