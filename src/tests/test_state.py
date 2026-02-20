"""
Тесты для модуля состояния (state.py).
"""

import pytest
from src.graph.state import AgentState


def test_agent_state_create():
    """Тест создания AgentState с минимальными полями."""
    state: AgentState = {
        "query": "Статья 330 ГК РФ",
        "trace": [],
    }
    assert state["query"] == "Статья 330 ГК РФ"
    assert state["trace"] == []


def test_agent_state_full():
    """Тест создания AgentState со всеми полями."""
    state: AgentState = {
        "query": "Взыскание неустойки",
        "law_type": "гражданское",
        "norms": [
            {
                "title": "ГК РФ Статья 330",
                "text": "Неустойкой признается...",
                "source": "ГК РФ",
                "url": "https://example.com",
            }
        ],
        "cases": [
            {
                "case_number": "А40-123456/2024",
                "title": "ООО «Ромашка» v. ООО «Вектор»",
                "summary": "Спор о неустойке",
                "url": "https://kad.arbitr.ru/Card/123456",
            }
        ],
        "answer": "Ответ на запрос",
        "trace": ["classify_query", "search_norms"],
    }
    assert state["law_type"] == "гражданское"
    assert len(state["norms"]) == 1
    assert len(state["cases"]) == 1
    assert "answer" in state


def test_agent_state_optional_fields():
    """Тест опциональных полей AgentState."""
    state: AgentState = {"query": "Тест"}
    # Опциональные поля могут отсутствовать
    assert "law_type" not in state or state.get("law_type") is None
    assert "error" not in state or state.get("error") is None


def test_agent_state_error():
    """Тест поля ошибки."""
    state: AgentState = {
        "query": "Тест",
        "error": "Произошла ошибка при поиске",
        "trace": ["classify_query"],
    }
    assert state["error"] == "Произошла ошибка при поиске"
