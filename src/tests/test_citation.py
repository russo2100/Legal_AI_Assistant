"""
Тесты для проверки цитирования (citation_check.py).
"""

import pytest
from src.tools.citation_check import CitationChecker, get_citation_checker


def test_citation_checker_init():
    """Тест инициализации checker."""
    checker = CitationChecker()
    assert checker is not None


def test_check_valid_citations():
    """Тест валидных цитат."""
    checker = CitationChecker()

    answer = "Согласно ст. 330 ГК РФ (https://www.consultant.ru/document/cons_doc_LAW_5142/)"
    norms = [
        {
            "title": "ГК РФ Статья 330",
            "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
            "source": "ГК РФ",
            "article_number": "330",
        }
    ]
    cases = []

    result = checker.check(answer, norms, cases)
    # Статья 330 ГК есть в источниках - должна быть валидной
    assert len(result.missing_citations) == 0 or result.is_valid


def test_check_missing_citations():
    """Тест отсутствующих цитат."""
    checker = CitationChecker()

    answer = "Согласно ст. 999 ГК РФ..."
    norms = [
        {
            "title": "ГК РФ Статья 330",
            "url": "https://www.consultant.ru/",
        }
    ]
    cases = []

    result = checker.check(answer, norms, cases)
    # Статья 999 не в источниках
    assert len(result.missing_citations) > 0 or not result.is_valid


def test_check_no_sources():
    """Тест без источников."""
    checker = CitationChecker()

    answer = "Некоторый ответ без ссылок"
    norms = []
    cases = []

    result = checker.check(answer, norms, cases)
    assert len(result.warnings) > 0


def test_verify_and_format():
    """Тест форматирования с проверкой."""
    checker = CitationChecker()

    answer = "Ответ по делу"
    norms = [{"title": "ГК", "url": "https://consultant.ru"}]
    cases = []

    formatted = checker.verify_and_format(answer, norms, cases)
    assert "Дисклеймер" in formatted or "дисclaimer" in formatted.lower()


def test_get_citation_checker_singleton():
    """Тест singleton для checker."""
    checker1 = get_citation_checker()
    checker2 = get_citation_checker()
    assert checker1 is checker2
