"""
Модуль LLM-клиентов для работы с несколькими провайдерами.

Основной провайдер: OpenRouter
Fallback провайдер: Perplexity

Пример использования:
    >>> from src.llm import get_llm_client
    >>> client = get_llm_client()
    >>> response = client.generate("Какой закон регулирует неустойку?")
    >>> print(response.content)
"""

from .client import LLMResponse, MultiLLMClient, OpenRouterClient, get_llm_client
from .perplexity_client import PerplexityClient, PerplexityResponse, get_perplexity_client

__all__ = [
    "LLMResponse",
    "MultiLLMClient",
    "OpenRouterClient",
    "PerplexityClient",
    "PerplexityResponse",
    "get_llm_client",
    "get_perplexity_client",
]
