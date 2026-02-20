"""
Модуль индексации кодексов в PostgreSQL/pgvector.

Загружает тексты нормативных актов, разбивает на чанки и сохраняет в БД.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

import psycopg2
from pgvector.psycopg2 import register_vector

from src.rag.embeddings import get_embedder

logger = logging.getLogger(__name__)


class CodeIndexer:
    """
    Индексатор кодексов для векторного поиска.

    Attributes:
        db_url: URL подключения к PostgreSQL.
        embedder: Эмбеддер для векторизации.
        chunk_size: Размер чанка в символах.
        chunk_overlap: Перекрытие между чанками.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Инициализирует индексатор.

        Args:
            db_url: URL подключения к PostgreSQL (из env если не указан).
            chunk_size: Размер чанка в символах.
            chunk_overlap: Перекрытие между чанками.
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "")
        self.embedder = get_embedder()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if not self.db_url:
            logger.warning("DATABASE_URL не установлен. Индексация будет недоступна.")

        self._conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> None:
        """Устанавливает подключение к БД и регистрирует pgvector."""
        if not self.db_url:
            raise ValueError("DATABASE_URL не установлен")

        self._conn = psycopg2.connect(self.db_url)
        register_vector(self._conn)
        logger.info("Подключение к PostgreSQL установлено, pgvector зарегистрирован")

    def close(self) -> None:
        """Закрывает подключение к БД."""
        if self._conn:
            self._conn.close()
            logger.info("Подключение к PostgreSQL закрыто")

    def create_tables(self) -> None:
        """Создаёт таблицы для хранения нормативных актов и чанков."""
        if not self._conn:
            self.connect()

        assert self._conn is not None

        with self._conn.cursor() as cur:
            # Таблица для кодексов
            cur.execute("""
                CREATE TABLE IF NOT EXISTS codes (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица для чанков с pgvector
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    code_id INTEGER REFERENCES codes(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    embedding vector(384),
                    article_number TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Индексы для быстрого поиска
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
                ON chunks USING ivfflat (embedding vector_cosine_ops)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_text_search 
                ON chunks USING gin (to_tsvector('russian', text))
            """)

            self._conn.commit()
            logger.info("Таблицы созданы, индексы построены")

    def chunk_text(self, text: str, title: str) -> list[dict]:
        """
        Разбивает текст на чанки с перекрытием.

        Args:
            text: Полный текст документа.
            title: Заголовок документа.

        Returns:
            Список чанков с метаданными.
        """
        chunks = []

        # Попытка разбить по статьям
        article_pattern = r"(Статья\s+\d+[^.]*\.)"
        articles = re.split(article_pattern, text)

        current_article = ""
        for i, part in enumerate(articles):
            if re.match(article_pattern, part):
                if current_article:
                    chunks.append({
                        "text": current_article.strip(),
                        "article_number": self._extract_article_number(current_article),
                    })
                current_article = part
            else:
                current_article += part

        if current_article.strip():
            chunks.append({
                "text": current_article.strip(),
                "article_number": self._extract_article_number(current_article),
            })

        # Если статей нет или они слишком большие, разбиваем по размеру
        final_chunks = []
        for chunk in chunks:
            text = chunk["text"]
            if len(text) > self.chunk_size * 2:
                # Разбиваем большой чанк
                for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                    segment = text[i : i + self.chunk_size]
                    if segment.strip():
                        final_chunks.append({
                            "text": segment.strip(),
                            "article_number": chunk["article_number"],
                        })
            else:
                final_chunks.append(chunk)

        logger.info(f"Разбито на {len(final_chunks)} чанков")
        return final_chunks

    def _extract_article_number(self, text: str) -> Optional[str]:
        """Извлекает номер статьи из текста."""
        match = re.search(r"Статья\s+(\d+)", text)
        return match.group(1) if match else None

    def index_code(self, file_path: str, code_type: str) -> int:
        """
        Индексирует файл с кодексом.

        Args:
            file_path: Путь к файлу с текстом кодекса.
            code_type: Тип кодекса (ГК, АПК, КоАП и т.д.).

        Returns:
            Количество проиндексированных чанков.
        """
        if not self._conn:
            self.connect()

        assert self._conn is not None

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        logger.info(f"Индексация файла: {file_path}")

        # Чтение файла
        text = path.read_text(encoding="utf-8")
        title = path.stem

        # Сохранение кодекса
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO codes (title, code_type) VALUES (%s, %s) RETURNING id",
                (title, code_type),
            )
            code_id = cur.fetchone()[0]
            self._conn.commit()

        # Чанкирование
        chunks = self.chunk_text(text, title)

        # Векторизация и сохранение чанков
        chunk_count = 0
        import json
        for i, chunk in enumerate(chunks):
            try:
                embedding = self.embedder.embed_text(chunk["text"])

                with self._conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chunks (code_id, text, embedding, article_number, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            code_id,
                            chunk["text"],
                            embedding,
                            chunk["article_number"],
                            json.dumps({"source": title, "chunk_index": i}),
                        ),
                    )
                    chunk_count += 1

                self._conn.commit()

                if chunk_count % 10 == 0:
                    logger.info(f"Обработано {chunk_count}/{len(chunks)} чанков")

            except Exception as e:
                logger.error(f"Ошибка при индексации чанка {i}: {e}")
                self._conn.rollback()

        logger.info(f"Проиндексировано {chunk_count} чанков из {title}")
        return chunk_count

    def index_directory(self, directory: str, code_type: Optional[str] = None) -> int:
        """
        Индексирует все файлы в директории.

        Args:
            directory: Путь к директории с кодексами.
            code_type: Тип кодекса (если не указан, определяется из имени файла).

        Returns:
            Общее количество проиндексированных чанков.
        """
        path = Path(directory)
        if not path.is_dir():
            raise NotADirectoryError(f"Не директория: {directory}")

        total_chunks = 0
        for file_path in path.glob("*.txt"):
            ctype = code_type or file_path.stem.upper()
            try:
                count = self.index_code(str(file_path), ctype)
                total_chunks += count
            except Exception as e:
                logger.error(f"Ошибка при индексации {file_path}: {e}")

        return total_chunks


def main() -> None:
    """CLI для индексации кодексов."""
    import argparse

    from dotenv import load_dotenv
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(description="Индексация кодексов в pgvector")
    parser.add_argument("--codes", default="data/codes", help="Путь к директории с кодексами")
    parser.add_argument("--type", dest="code_type", default=None, help="Тип кодекса (опционально)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # UTF-8 для Windows
    import sys, io
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except:
            pass

    indexer = CodeIndexer()
    try:
        indexer.create_tables()
        count = indexer.index_directory(args.codes, args.code_type)
        print(f"✅ Проиндексировано {count} чанков")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        indexer.close()


if __name__ == "__main__":
    main()
