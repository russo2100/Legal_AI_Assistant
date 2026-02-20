"""
Модуль получения эмбеддингов через OpenRouter API или локально.

Использует модель qwen-embed через API или sentence-transformers локально.
"""

import logging
import os
import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class OpenRouterEmbedder:
    """
    Эмбеддер для получения векторов через OpenRouter API или локально.

    Attributes:
        api_key: API-ключ OpenRouter.
        model: Название модели для эмбеддингов.
        base_url: Базовый URL API OpenRouter.
        use_local: Использовать локальную модель.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        use_local: bool = False,
    ):
        """
        Инициализирует эмбеддер.

        Args:
            api_key: API-ключ OpenRouter (из env если не указан).
            model: Модель для эмбеддингов (по умолчанию qwen-embed).
            base_url: Базовый URL API.
            use_local: Использовать локальную модель.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("EMBEDDING_MODEL", "")
        self.base_url = base_url
        self.use_local = use_local or not self.model

        self._client = httpx.Client(timeout=30.0, headers=self._get_headers())
        self._local_model = None

        # Если нет модели или указана локальная - используем sentence-transformers
        if self.use_local or "local" in self.model.lower():
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.use_local = True
                logger.info("Используется локальная модель для эмбеддингов")
            except ImportError:
                logger.warning("sentence-transformers не установлен. Установите: pip install sentence-transformers")
                self.use_local = False

        if not self.api_key and not self.use_local:
            logger.warning("OPENROUTER_API_KEY не установлен. Эмбеддинги будут недоступны.")

    def _get_headers(self) -> dict[str, str]:
        """Возвращает заголовки для API-запросов."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yurik-legal-agent",
            "X-Title": "Legal RAG Agent",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def embed_text(self, text: str) -> list[float]:
        """
        Получает векторное представление текста.

        Args:
            text: Текст для векторизации.

        Returns:
            Вектор размерности 1536 (API) или 384 (локально).

        Raises:
            httpx.HTTPStatusError: При ошибке API.
            httpx.TimeoutException: При таймауте запроса.
        """
        # Локальная модель
        if self.use_local and self._local_model:
            logger.debug(f"Локальная векторизация текста длиной {len(text)}")
            embedding = self._local_model.encode(text, convert_to_numpy=True).tolist()
            logger.debug(f"Получен вектор размерности {len(embedding)}")
            return embedding

        logger.debug(f"Получение эмбеддинга через API для текста длиной {len(text)}")

        # Rate limiting
        time.sleep(2.0)  # 1 запрос в 2 секунды

        response = self._client.post(
            f"{self.base_url}/embeddings",
            json={
                "model": self.model,
                "input": text,
            },
        )
        response.raise_for_status()

        data = response.json()
        embedding = data["data"][0]["embedding"]

        logger.debug(f"Получен вектор размерности {len(embedding)}")
        return embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Получает векторные представления для списка текстов.

        Args:
            texts: Список текстов для векторизации.

        Returns:
            Список векторов.
        """
        logger.info(f"Получение эмбеддингов для {len(texts)} текстов")
        embeddings = []
        for i, text in enumerate(texts):
            try:
                emb = self.embed_text(text)
                embeddings.append(emb)
                logger.debug(f"Обработан текст {i + 1}/{len(texts)}")
            except Exception as e:
                logger.error(f"Ошибка при векторизации текста {i}: {e}")
                # Заглушка при ошибке (размерность зависит от модели)
                dim = 384 if self.use_local else 1536
                embeddings.append([0.0] * dim)
        return embeddings


# Глобальный экземпляр для использования в других модулях
_embedder: Optional[OpenRouterEmbedder] = None


def get_embedder() -> OpenRouterEmbedder:
    """Возвращает глобальный экземпляр эмбеддера."""
    global _embedder
    if _embedder is None:
        _embedder = OpenRouterEmbedder()
    return _embedder
