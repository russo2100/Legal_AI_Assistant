"""
Парсер картотеки арбитражных дел kad.arbitr.ru.

Асинхронный парсинг с rate limiting для поиска судебной практики.
"""

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CaseResult:
    """Результат поиска дела."""

    case_number: str
    title: str
    summary: str
    url: str
    date: Optional[str] = None
    court: Optional[str] = None
    parties: list[str] = field(default_factory=list)
    raw_html: Optional[str] = None


class KadParser:
    """
    Парсер картотеки арбитражных дел kad.arbitr.ru.

    Attributes:
        base_url: Базовый URL картотеки.
        rate_limit: Задержек между запросами в секундах.
        timeout: Таймаут запроса в секундах.
    """

    def __init__(
        self,
        base_url: str = "https://kad.arbitr.ru",
        rate_limit: float = 2.0,
        timeout: float = 30.0,
    ):
        """
        Инициализирует парсер.

        Args:
            base_url: Базовый URL картотеки.
            rate_limit: Задержка между запросами (сек).
            timeout: Таймаут запроса.
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._last_request_time: float = 0

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

    async def _rate_limited_request(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        """
        Выполняет запрос с rate limiting.

        Args:
            url: URL запроса.
            params: Параметры запроса.

        Returns:
            HTTP-ответ.
        """
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)

        self._last_request_time = time.time()

        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response

    async def search_cases(self, query: str, limit: int = 5) -> list[CaseResult]:
        """
        Ищет дела по запросу.

        Args:
            query: Поисковый запрос (номер дела или ключевые слова).
            limit: Количество результатов.

        Returns:
            Список найденных дел.
        """
        logger.info(f"Поиск дел: query={query}, limit={limit}")

        # Если это номер дела (формат А40-123456/2024)
        case_match = re.match(r"А\d+-\d+/\d{4}", query, re.IGNORECASE)

        if case_match:
            # Прямой поиск по номеру дела
            return await self._get_case_by_number(query.upper())
        else:
            # Текстовый поиск
            return await self._search_by_text(query, limit)

    async def _get_case_by_number(self, case_number: str) -> list[CaseResult]:
        """Получает информацию по номеру дела."""
        url = f"{self.base_url}/Card/{case_number}"

        try:
            response = await self._rate_limited_request(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Извлечение данных
            title = self._extract_title(soup)
            summary = self._extract_summary(soup)
            date = self._extract_date(soup)
            court = self._extract_court(soup)
            parties = self._extract_parties(soup)

            case = CaseResult(
                case_number=case_number,
                title=title,
                summary=summary,
                url=url,
                date=date,
                court=court,
                parties=parties,
            )

            logger.info(f"Найдено дело: {case_number}")
            return [case]

        except httpx.HTTPError as e:
            logger.warning(f"Дело не найдено или ошибка запроса: {case_number}, {e}")
            return []

    async def _search_by_text(self, query: str, limit: int) -> list[CaseResult]:
        """Выполняет текстовый поиск по делам."""
        url = f"{self.base_url}/"
        params = {
            "Page": 1,
            "Size": limit,
            "txtInput": query,
        }

        try:
            response = await self._rate_limited_request(url, params=params)
            soup = BeautifulSoup(response.text, "lxml")

            results = []
            case_cards = soup.select(".card_block, .result_item")

            for card in case_cards[:limit]:
                case_data = self._parse_search_result(card, url)
                if case_data:
                    results.append(case_data)

            logger.info(f"Текстовый поиск вернул {len(results)} результатов")
            return results

        except httpx.HTTPError as e:
            logger.error(f"Ошибка при текстовом поиске: {e}")
            return []

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Извлекает заголовок дела."""
        title_elem = soup.select_one(".delo_title, h1")
        return title_elem.get_text(strip=True) if title_elem else "Без названия"

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Извлекает краткое описание дела."""
        # Попытка найти категорию дела
        category = soup.select_one(".delo_category")
        if category:
            return category.get_text(strip=True)

        # Или первое описание
        desc = soup.select_one(".description, .info")
        return desc.get_text(strip=True)[:500] if desc else "Описание недоступно"

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает дату дела."""
        date_elem = soup.select_one(".date, .delo_date")
        if date_elem:
            return date_elem.get_text(strip=True)
        return None

    def _extract_court(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает информацию о суде."""
        court_elem = soup.select_one(".court, .arbitr_court")
        return court_elem.get_text(strip=True) if court_elem else None

    def _extract_parties(self, soup: BeautifulSoup) -> list[str]:
        """Извлекает стороны дела."""
        parties = []

        # Истец
        plaintiff = soup.select_one(".plaintiff, .istec")
        if plaintiff:
            parties.append(f"Истец: {plaintiff.get_text(strip=True)}")

        # Ответчик
        defendant = soup.select_one(".defendant, .otvetchik")
        if defendant:
            parties.append(f"Ответчик: {defendant.get_text(strip=True)}")

        return parties

    def _parse_search_result(self, card, base_url: str) -> Optional[CaseResult]:
        """Парсит результат поиска из списка."""
        # Номер дела
        number_elem = card.select_one(".number, .case_number a")
        if not number_elem:
            return None

        case_number = number_elem.get_text(strip=True)
        href = number_elem.get("href", "")
        url = f"{base_url}{href}" if href.startswith("/") else href

        # Заголовок/описание
        title_elem = card.select_one(".title, .truncated")
        title = title_elem.get_text(strip=True) if title_elem else case_number

        # Дата
        date_elem = card.select_one(".date")
        date = date_elem.get_text(strip=True) if date_elem else None

        return CaseResult(
            case_number=case_number,
            title=title,
            summary="См. картотеку дел",
            url=url,
            date=date,
        )

    async def close(self) -> None:
        """Закрывает HTTP-клиент."""
        await self._client.aclose()
        logger.info("KadParser закрыт")


# Синхронная обёртка для использования в nodes.py
class KadParserSync:
    """Синхронная обёртка для KadParser."""

    def __init__(self):
        self._parser = KadParser()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def search_cases(self, query: str, limit: int = 5) -> list[dict]:
        """
        Ищет дела (синхронная версия).

        Args:
            query: Поисковый запрос.
            limit: Количество результатов.

        Returns:
            Список дел в формате dict.
        """
        loop = self._get_loop()
        results = loop.run_until_complete(self._parser.search_cases(query, limit))

        return [
            {
                "case_number": r.case_number,
                "title": r.title,
                "summary": r.summary,
                "url": r.url,
                "date": r.date,
                "court": r.court,
            }
            for r in results
        ]

    def close(self) -> None:
        """Закрывает парсер."""
        loop = self._get_loop()
        loop.run_until_complete(self._parser.close())


# Глобальный экземпляр
_parser: Optional[KadParserSync] = None


def get_kad_parser() -> KadParserSync:
    """Возвращает глобальный экземпляр парсера."""
    global _parser
    if _parser is None:
        _parser = KadParserSync()
    return _parser
