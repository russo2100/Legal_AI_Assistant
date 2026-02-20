"""
Тесты для узлов графа (nodes.py).
"""

import pytest
from src.graph.nodes import (
    classify_query,
    search_norms,
    search_cases,
    generate_answer,
    verify_citation,
)


def test_classify_query_civil():
    """Тест классификации гражданского запроса."""
    state = {"query": "Статья 330 ГК РФ неустойка", "trace": []}
    result = classify_query(state)
    assert result["law_type"] == "гражданское"
    assert "classify_query" in result["trace"]


def test_classify_query_arbitration():
    """Тест классификации арбитражного запроса."""
    state = {"query": "Дело А40-123456/2024 kad.arbitr.ru", "trace": []}
    result = classify_query(state)
    assert result["law_type"] == "арбитражное"


def test_classify_query_administrative():
    """Тест классификации административного запроса."""
    state = {"query": "Штраф по КоАП нарушение", "trace": []}
    result = classify_query(state)
    assert result["law_type"] == "административное"


def test_search_norms_article_330():
    """Тест поиска нормы - статья 330 ГК."""
    state = {"query": "Статья 330 ГК РФ", "law_type": "гражданское", "trace": []}
    result = search_norms(state)
    assert len(result["norms"]) > 0
    assert "330" in result["norms"][0]["title"]
    assert "search_norms" in result["trace"]


def test_search_norms_empty():
    """Тест поиска без результатов."""
    state = {"query": "Несуществующий запрос XYZ", "law_type": "гражданское", "trace": []}
    result = search_norms(state)
    # Заглушка может вернуть пустой результат
    assert "norms" in result
    assert "search_norms" in result["trace"]


def test_search_cases_with_penalty():
    """Тест поиска дел о неустойке."""
    state = {"query": "Взыскание неустойки по договору", "trace": []}
    result = search_cases(state)
    # Заглушка возвращает дело для запросов о неустойке
    assert "cases" in result
    assert "search_cases" in result["trace"]


def test_generate_answer_with_norms():
    """Тест генерации ответа с нормами."""
    state = {
        "query": "Статья 330 ГК",
        "law_type": "гражданское",
        "norms": [
            {
                "title": "ГК РФ Статья 330",
                "text": "Неустойкой признается...",
                "source": "ГК РФ",
                "url": "https://consultant.ru",
            }
        ],
        "cases": [],
        "trace": [],
    }
    result = generate_answer(state)
    assert "answer" in result
    assert "ГК РФ Статья 330" in result["answer"]
    assert "Disclaimer" in result["answer"] or "disclaimer" in result["answer"].lower()
    assert "generate_answer" in result["trace"]


def test_generate_answer_no_norms():
    """Тест генерации ответа без норм."""
    state = {
        "query": "Неизвестный запрос",
        "law_type": "гражданское",
        "norms": [],
        "cases": [],
        "trace": [],
    }
    result = generate_answer(state)
    assert "answer" in result
    assert "no specific norms" in result["answer"].lower() or "normative base" in result["answer"].lower()


def test_verify_citation():
    """Тест проверки цитирования."""
    state = {
        "query": "Тест",
        "norms": [{"title": "ГК", "url": "https://example.com"}],
        "cases": [],
        "trace": [],
    }
    result = verify_citation(state)
    assert "verify_citation" in result["trace"]


def test_full_chain():
    """Тест полной цепочки узлов."""
    state = {"query": "Статья 330 ГК РФ неустойка", "norms": [], "cases": [], "trace": []}

    state = classify_query(state)
    state = search_norms(state)
    state = search_cases(state)
    state = generate_answer(state)
    state = verify_citation(state)

    assert len(state["trace"]) == 5
    assert state["trace"] == [
        "classify_query",
        "search_norms",
        "search_cases",
        "generate_answer",
        "verify_citation",
    ]
    assert "answer" in state
