"""
Модуль проверки корректности цитирования источников.

Проверяет, что все ссылки в ответе соответствуют найденным нормам и делам.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CitationCheckResult:
    """Результат проверки цитирования."""

    is_valid: bool
    missing_citations: list[str]
    invalid_urls: list[str]
    warnings: list[str]


class CitationChecker:
    """
    Проверка цитирования в ответах агента.

    Убеждается, что все упомянутые источники присутствуют в retrieved context.
    """

    def __init__(self):
        """Инициализирует checker."""
        # Паттерны для извлечения ссылок
        self.url_pattern = re.compile(r"https?://[^\s\)]+")
        self.article_pattern = re.compile(r"(?:ст\.?\s*|статья\s+)(\d+(?:-\d+)?)", re.IGNORECASE)
        self.code_pattern = re.compile(r"\b(ГК|АПК|ГПК|КоАП|УК|УПК)\b", re.IGNORECASE)

    def check(
        self,
        answer: str,
        norms: list[dict],
        cases: list[dict],
    ) -> CitationCheckResult:
        """
        Проверяет цитирование в ответе.

        Args:
            answer: Текст ответа.
            norms: Список найденных норм.
            cases: Список найденных дел.

        Returns:
            Результат проверки.
        """
        logger.info(f"Проверка цитирования: norms={len(norms)}, cases={len(cases)}")

        missing_citations = []
        invalid_urls = []
        warnings = []

        # Извлекаем все URL из ответа
        found_urls = set(self.url_pattern.findall(answer))

        # Собираем валидные URL из источников
        valid_urls = set()
        for norm in norms:
            if norm.get("url"):
                valid_urls.add(norm["url"])
        for case in cases:
            if case.get("url"):
                valid_urls.add(case["url"])

        # Проверяем каждый найденный URL
        for url in found_urls:
            # Очищаем URL от markdown-синтаксиса
            url = url.rstrip(")")
            if url not in valid_urls and "consultant.ru" not in url and "kad.arbitr.ru" not in url:
                invalid_urls.append(url)

        # Проверяем упоминания статей
        mentioned_articles = self._extract_article_mentions(answer)
        available_articles = self._get_available_articles(norms)

        for code, article in mentioned_articles:
            if (code, article) not in available_articles:
                missing_citations.append(f"{code} ст.{article}")

        # Предупреждения
        if not norms and not cases:
            warnings.append("Ответ не содержит ссылок на источники")

        if len(found_urls) > len(valid_urls) * 2:
            warnings.append("Подозрительно большое количество ссылок в ответе")

        is_valid = len(missing_citations) == 0 and len(invalid_urls) == 0

        result = CitationCheckResult(
            is_valid=is_valid,
            missing_citations=missing_citations,
            invalid_urls=invalid_urls,
            warnings=warnings,
        )

        logger.info(f"Проверка завершена: valid={is_valid}, missing={len(missing_citations)}")
        return result

    def _extract_article_mentions(self, text: str) -> list[tuple[str, str]]:
        """
        Извлекает упоминания статей из текста.

        Returns:
            Список кортежей (кодекс, номер статьи).
        """
        mentions = []

        # Находим все упоминания кодексов
        for match in self.code_pattern.finditer(text):
            code = match.group(1).upper()
            start = match.start()

            # Ищем номер статьи рядом
            nearby_text = text[max(0, start - 50) : start + 50]
            article_match = self.article_pattern.search(nearby_text)

            if article_match:
                article = article_match.group(1)
                mentions.append((code, article))

        return mentions

    def _get_available_articles(self, norms: list[dict]) -> set[tuple[str, str]]:
        """
        Получает множество доступных статей из норм.

        Returns:
            Множество кортежей (кодекс, номер статьи).
        """
        articles = set()

        for norm in norms:
            source = norm.get("source", "")
            article = norm.get("article_number")

            # Извлекаем кодекс из источника
            code_match = self.code_pattern.search(source)
            if code_match:
                code = code_match.group(1).upper()

                # Если номер статьи не указан явно, пробуем извлечь
                if not article:
                    article_match = self.article_pattern.search(source)
                    if article_match:
                        article = article_match.group(1)

                if article:
                    articles.add((code, article))

        return articles

    def verify_and_format(
        self,
        answer: str,
        norms: list[dict],
        cases: list[dict],
        disclaimer: str = "Аналитическая подсказка. Требуется проверка юристом.",
    ) -> str:
        """
        Проверяет и форматирует ответ с добавлением статуса проверки.

        Args:
            answer: Исходный ответ.
            norms: Список норм.
            cases: Список дел.
            disclaimer: Текст дисклеймера.

        Returns:
            Отформатированный ответ со статусом проверки.
        """
        result = self.check(answer, norms, cases)

        # Добавляем статус проверки
        if result.is_valid:
            verification_status = "✅ Все источники проверены"
        else:
            verification_status = "⚠️ Требуется дополнительная проверка источников"
            if result.missing_citations:
                verification_status += f"\n\nОтсутствуют ссылки: {', '.join(result.missing_citations)}"

        # Добавляем дисклеймер
        full_answer = f"{answer}\n\n---\n\n{verification_status}\n\n> ⚠️ **Дисклеймер:** {disclaimer}"

        return full_answer


# Глобальный экземпляр
_checker: Optional[CitationChecker] = None


def get_citation_checker() -> CitationChecker:
    """Возвращает глобальный экземпляр checker."""
    global _checker
    if _checker is None:
        _checker = CitationChecker()
    return _checker
