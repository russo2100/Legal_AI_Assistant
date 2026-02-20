"""
Модуль гибридного поиска по кодексам (BM25 + pgvector).

Реализует комбинированный поиск с reranking результатов.
"""

import logging
import os
from typing import Optional

import psycopg2
from pgvector.psycopg2 import register_vector
from rank_bm25 import BM25Okapi

from src.rag.embeddings import get_embedder

logger = logging.getLogger(__name__)


class LegalRetriever:
    """
    Ретривер для гибридного поиска по нормативным актам.

    Combines BM25 lexical search with pgvector semantic search.
    """

    def __init__(self, db_url: Optional[str] = None, top_k: int = 5):
        """
        Инициализирует ретривер.

        Args:
            db_url: URL подключения к PostgreSQL.
            top_k: Количество возвращаемых результатов.
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "")
        self.top_k = top_k
        self.embedder = get_embedder()

        self._conn: Optional[psycopg2.extensions.connection] = None
        self._bm25_index: Optional[BM25Okapi] = None
        self._bm25_documents: list[str] = []

    def connect(self) -> None:
        """Устанавливает подключение к БД."""
        if not self.db_url:
            raise ValueError("DATABASE_URL не установлен")

        self._conn = psycopg2.connect(self.db_url)
        register_vector(self._conn)
        logger.info("Подключение к PostgreSQL установлено")

    def close(self) -> None:
        """Закрывает подключение к БД."""
        if self._conn:
            self._conn.close()
            logger.info("Подключение к PostgreSQL закрыто")

    def build_bm25_index(self) -> int:
        """
        Строит BM25-индекс в памяти.

        Returns:
            Количество документов в индексе.
        """
        if not self._conn:
            self.connect()

        assert self._conn is not None

        logger.info("Построение BM25-индекса...")

        with self._conn.cursor() as cur:
            cur.execute("SELECT id, text FROM chunks")
            rows = cur.fetchall()

        self._bm25_documents = [row[1] for row in rows]
        tokenized_docs = [doc.lower().split() for doc in self._bm25_documents]
        self._bm25_index = BM25Okapi(tokenized_docs)

        logger.info(f"BM25-индекс построен для {len(self._bm25_documents)} документов")
        return len(self._bm25_documents)

    def search_vector(self, query: str, limit: int = 10) -> list[dict]:
        """
        Выполняет векторный поиск.

        Args:
            query: Поисковый запрос.
            limit: Количество результатов.

        Returns:
            Список найденных чанков.
        """
        if not self._conn:
            self.connect()

        assert self._conn is not None

        query_embedding = self.embedder.embed_text(query)

        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, text, article_number, metadata, 
                       1 - (embedding <=> %s::vector) as similarity
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))

            rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "text": row[1],
                "article_number": row[2],
                "metadata": row[3],
                "similarity": row[4],
                "search_type": "vector",
            })

        logger.info(f"Векторный поиск вернул {len(results)} результатов")
        return results

    def search_bm25(self, query: str, limit: int = 10) -> list[dict]:
        """
        Выполняет BM25-поиск.

        Args:
            query: Поисковый запрос.
            limit: Количество результатов.

        Returns:
            Список найденных чанков.
        """
        if not self._bm25_index:
            self.build_bm25_index()

        assert self._bm25_index is not None

        query_tokens = query.lower().split()
        scores = self._bm25_index.get_scores(query_tokens)

        # Топ-k результатов
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:limit]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "id": idx,
                    "text": self._bm25_documents[idx],
                    "article_number": None,
                    "metadata": {},
                    "similarity": float(scores[idx]),
                    "search_type": "bm25",
                })

        logger.info(f"BM25-поиск вернул {len(results)} результатов")
        return results

    def hybrid_search(self, query: str, alpha: float = 0.5) -> list[dict]:
        """
        Выполняет гибридный поиск с комбинацией векторного и BM25.

        Args:
            query: Поисковый запрос.
            alpha: Вес векторного поиска (0 = только BM25, 1 = только вектор).

        Returns:
            Список найденных чанков с комбинированным scoring.
        """
        logger.info(f"Гибридный поиск: query={query}, alpha={alpha}")

        # Получаем результаты обоих поисков
        vector_results = self.search_vector(query, limit=self.top_k * 2)
        bm25_results = self.search_bm25(query, limit=self.top_k * 2)

        # Объединяем результаты
        all_results = {}

        for res in vector_results:
            all_results[res["id"]] = {
                **res,
                "vector_score": res["similarity"],
                "bm25_score": 0.0,
            }

        for res in bm25_results:
            if res["id"] in all_results:
                all_results[res["id"]]["bm25_score"] = res["similarity"]
            else:
                all_results[res["id"]] = {
                    **res,
                    "vector_score": 0.0,
                    "bm25_score": res["similarity"],
                }

        # Нормализация и комбинация скоров
        max_vector = max((r["vector_score"] for r in all_results.values()), default=1)
        max_bm25 = max((r["bm25_score"] for r in all_results.values()), default=1)

        for res in all_results.values():
            norm_vector = res["vector_score"] / max_vector if max_vector > 0 else 0
            norm_bm25 = res["bm25_score"] / max_bm25 if max_bm25 > 0 else 0
            res["combined_score"] = alpha * norm_vector + (1 - alpha) * norm_bm25

        # Сортировка и возврат топ-k
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True,
        )[: self.top_k]

        logger.info(f"Гибридный поиск вернул {len(sorted_results)} результатов")
        return sorted_results

    def retrieve(self, query: str, law_type: Optional[str] = None) -> list[dict]:
        """
        Основной метод для поиска норм по запросу.

        Args:
            query: Поисковый запрос.
            law_type: Тип права для фильтрации.

        Returns:
            Список найденных норм с метаданными.
        """
        if not self._conn:
            self.connect()

        results = self.hybrid_search(query)

        # Формирование ответа в формате для nodes.py
        norms = []
        for res in results:
            metadata = res.get("metadata", {})
            source = metadata.get("source", "Неизвестный источник")

            norms.append({
                "title": f"{source}, Статья {res.get('article_number', 'б/н')}",
                "text": res["text"],
                "source": source,
                "url": self._generate_consultant_url(source, res.get("article_number")),
                "score": res.get("combined_score", 0),
            })

        return norms

    def _generate_consultant_url(self, source: str, article_number: Optional[str]) -> str:
        """Генерирует ссылку на Consultant.ru."""
        base_urls = {
            "ГК": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
            "АПК": "https://www.consultant.ru/document/cons_doc_LAW_121386/",
            "ГПК": "https://www.consultant.ru/document/cons_doc_LAW_39570/",
            "КоАП": "https://www.consultant.ru/document/cons_doc_LAW_34661/",
        }

        for code, url in base_urls.items():
            if code in source.upper():
                return url

        return "https://www.consultant.ru/"


# Глобальный экземпляр
_retriever: Optional[LegalRetriever] = None


def get_retriever() -> LegalRetriever:
    """Возвращает глобальный экземпляр ретривера."""
    global _retriever
    if _retriever is None:
        _retriever = LegalRetriever()
    return _retriever
