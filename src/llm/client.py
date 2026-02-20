"""
LLM-клиент для работы с OpenRouter API.

Поддержка retry/backoff, rate limiting и обработки ошибок.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Ответ от LLM."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str


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
        self._rate_limit: float = 2.0  # 1 запрос в 2 секунды

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

        logger.debug(f"Запрос к LLM: {len(prompt)} символов")

        data = self._make_request(messages, **kwargs)

        choice = data["choices"][0]
        usage = data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

        response = LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=usage,
            finish_reason=choice.get("finish_reason", "stop"),
        )

        logger.info(f"LLM ответ: {len(response.content)} символов, tokens={usage.get('total_tokens', 0)}")
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


# Глобальный экземпляр
_client: Optional[OpenRouterClient] = None


def get_llm_client() -> OpenRouterClient:
    """Возвращает глобальный экземпляр клиента."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client
