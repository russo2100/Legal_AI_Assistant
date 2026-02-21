"""
LLM-клиент с fallback-логикой для работы с несколькими провайдерами.

Основной провайдер: OpenRouter
Fallback провайдер: Perplexity

При недоступности основного провайдера автоматически переключается на fallback.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .perplexity_client import PerplexityClient, PerplexityResponse

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Ответ от LLM."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str
    provider: str  # "openrouter" или "perplexity"


class OpenRouterClient:
    """
    Клиент для OpenRouter API.

    Attributes:
        api_key: API-ключ OpenRouter.
        model: Модель по умолчанию.
        base_url: Базовый URL API.
        temperature: Температура генерации.
        max_tokens: Максимальное количество токенов.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        """
        Инициализирует клиент.

        Args:
            api_key: API-ключ (из env если не указан).
            model: Модель по умолчанию.
            base_url: Базовый URL API.
            temperature: Температура генерации.
            max_tokens: Максимум токенов в ответе.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._last_request_time: float = 0
        self._rate_limit: float = float(os.getenv("OPENROUTER_RATE_LIMIT", "2.0"))

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY не установлен. LLM будет недоступна.")

        self._client = httpx.Client(
            timeout=httpx.Timeout(60.0),
            headers=self._get_headers(),
        )

    def _get_headers(self) -> dict[str, str]:
        """Возвращает заголовки для API-запросов."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yurik-legal-agent",
            "X-Title": "Legal RAG Agent",
        }

    def _apply_rate_limit(self) -> None:
        """Применяет rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        reraise=True,
    )
    def _make_request(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        """
        Выполняет запрос к API.

        Args:
            messages: Список сообщений в формате OpenAI.
            **kwargs: Дополнительные параметры.

        Returns:
            JSON-ответ от API.
        """
        self._apply_rate_limit()

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        response = self._client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Генерирует ответ на промпт.

        Args:
            prompt: Пользовательский промпт.
            system_prompt: Системный промпт.
            **kwargs: Дополнительные параметры.

        Returns:
            LLMResponse с ответом.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        logger.debug(f"OpenRouter запрос: {len(prompt)} символов")

        data = self._make_request(messages, **kwargs)

        choice = data["choices"][0]
        usage = data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

        response = LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=usage,
            finish_reason=choice.get("finish_reason", "stop"),
            provider="openrouter",
        )

        logger.info(f"OpenRouter ответ: {len(response.content)} символов, tokens={usage.get('total_tokens', 0)}")
        return response

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Генерирует JSON-ответ.

        Args:
            prompt: Пользовательский промпт.
            system_prompt: Системный промпт.
            **kwargs: Дополнительные параметры.

        Returns:
            Распарсенный JSON.
        """
        import json

        # Добавляем инструкцию для JSON
        json_instruction = "\n\nОтветь ТОЛЬКО валидным JSON без markdown-форматирования."

        response = self.generate(
            prompt + json_instruction,
            system_prompt=system_prompt,
            temperature=0.0,  # Детерминированный ответ для JSON
            **kwargs,
        )

        # Парсинг JSON
        content = response.content.strip()

        # Удаление markdown-блоков если есть
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return {"error": "Failed to parse JSON response", "raw": content}


class MultiLLMClient:
    """
    Клиент с fallback-логикой для нескольких LLM-провайдеров.

    Сначала пытается использовать основной провайдер (OpenRouter).
    При неудаче переключается на fallback (Perplexity).

    Attributes:
        primary_client: Основной клиент (OpenRouter).
        fallback_client: Fallback клиент (Perplexity).
    """

    def __init__(self):
        """Инициализирует клиент с двумя провайдерами."""
        self.primary_client = OpenRouterClient(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=os.getenv("OPENROUTER_MODEL"),
        )
        
        self.fallback_client = PerplexityClient(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            model=os.getenv("PERPLEXITY_MODEL"),
        )
        
        logger.info("MultiLLMClient инициализирован с fallback-логикой")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """
        Генерирует ответ с fallback-логикой.

        Args:
            prompt: Пользовательский промпт.
            system_prompt: Системный промпт.
            use_fallback: Использовать ли fallback при ошибке.
            **kwargs: Дополнительные параметры.

        Returns:
            LLMResponse с ответом.

        Raises:
            RuntimeError: Если все провайдеры недоступны.
        """
        # Попытка использовать основной провайдер
        try:
            logger.info("Попытка использования OpenRouter...")
            response = self.primary_client.generate(prompt, system_prompt, **kwargs)
            return response
        except Exception as e:
            logger.warning(f"OpenRouter недоступен: {e}")
            
            if not use_fallback:
                raise
            
            # Попытка использовать fallback-провайдер
            logger.info("Переключение на Perplexity (fallback)...")
            try:
                perplexity_response = self.fallback_client.generate(prompt, system_prompt, **kwargs)
                
                # Конвертируем PerplexityResponse в LLMResponse
                return LLMResponse(
                    content=perplexity_response.content,
                    model=perplexity_response.model,
                    usage=perplexity_response.usage,
                    finish_reason=perplexity_response.finish_reason,
                    provider="perplexity",
                )
            except Exception as fallback_error:
                logger.error(f"Perplexity также недоступен: {fallback_error}")
                raise RuntimeError(
                    "Все LLM-провайдеры недоступны. "
                    f"OpenRouter ошибка: {e}, Perplexity ошибка: {fallback_error}"
                )

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs,
    ) -> Any:
        """
        Генерирует JSON-ответ с fallback-логикой.

        Args:
            prompt: Пользовательский промпт.
            system_prompt: Системный промпт.
            use_fallback: Использовать ли fallback при ошибке.
            **kwargs: Дополнительные параметры.

        Returns:
            Распарсенный JSON.
        """
        import json

        # Добавляем инструкцию для JSON
        json_instruction = "\n\nОтветь ТОЛЬКО валидным JSON без markdown-форматирования."

        response = self.generate(
            prompt + json_instruction,
            system_prompt=system_prompt,
            use_fallback=use_fallback,
            temperature=0.0,
            **kwargs,
        )

        # Парсинг JSON
        content = response.content.strip()

        # Удаление markdown-блоков если есть
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return {"error": "Failed to parse JSON response", "raw": content}


# Глобальный экземпляр
_client: Optional[MultiLLMClient] = None


def get_llm_client() -> MultiLLMClient:
    """
    Возвращает глобальный экземпляр клиента с fallback-логикой.

    Returns:
        MultiLLMClient для генерации ответов.
    """
    global _client
    if _client is None:
        _client = MultiLLMClient()
    return _client
