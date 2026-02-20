"""
Точка входа CLI для юридического RAG-агента.

Использование:
    python -m src.main "Статья 330 ГК РФ неустойка"
"""

import logging
import sys
import os
import io
from pathlib import Path

from dotenv import load_dotenv

from src.graph.workflow import get_compiled_graph
from src.utils.logging_config import setup_logging

# Загрузка переменных окружения с перезаписью
load_dotenv(override=True)

# Установка UTF-8 для Windows
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul 2>&1")
    except:
        pass
    # Перекодировка stdout для поддержки UTF-8
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass


def main() -> None:
    """Запускает юридический агент с запросом из командной строки."""
    setup_logging()
    logger = logging.getLogger(__name__)

    if len(sys.argv) < 2:
        print("Usage: python -m src.main \"your query\"")
        print("Example: python -m src.main \"Statya 330 GK RF neustoyka\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    logger.info(f"Received query: {query}")

    try:
        graph = get_compiled_graph()
        result = graph.invoke({"query": query, "norms": [], "cases": [], "trace": []})

        print("\n" + "=" * 60)
        print(result["answer"])
        print("=" * 60)
        print(f"\nTrace: {' -> '.join(result.get('trace', []))}")

        logger.info("Request processed successfully")

    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
