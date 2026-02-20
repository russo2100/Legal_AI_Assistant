"""
Тесты для графа LangGraph (workflow.py).
"""

import pytest
from src.graph.workflow import build_workflow, get_compiled_graph
from src.graph.state import AgentState


def test_build_workflow():
    """Тест построения графа."""
    graph = build_workflow()
    assert graph is not None


def test_compiled_graph():
    """Тест скомпилированного графа."""
    graph = get_compiled_graph()
    assert graph is not None


def test_graph_invoke():
    """Тест выполнения графа."""
    graph = get_compiled_graph()

    result = graph.invoke({
        "query": "Статья 330 ГК РФ",
        "norms": [],
        "cases": [],
        "trace": [],
    })

    assert isinstance(result, dict)
    assert "query" in result
    assert "answer" in result
    assert "trace" in result
    assert len(result["trace"]) > 0


def test_graph_trace_order():
    """Тест порядка узлов в trace."""
    graph = get_compiled_graph()

    result = graph.invoke({
        "query": "Взыскание неустойки ГК РФ",
        "norms": [],
        "cases": [],
        "trace": [],
    })

    expected_order = ["classify_query", "search_norms", "search_cases", "generate_answer", "verify_citation"]
    assert result["trace"] == expected_order


def test_graph_law_type_detection():
    """Тест определения типа права в графе."""
    graph = get_compiled_graph()

    # Гражданское
    result = graph.invoke({"query": "Статья 330 ГК", "norms": [], "cases": [], "trace": []})
    assert result["law_type"] == "гражданское"

    # Арбитражное
    result = graph.invoke({"query": "Дело А40-12345/2024", "norms": [], "cases": [], "trace": []})
    assert result["law_type"] == "арбитражное"


def test_graph_empty_query():
    """Тест с пустым запросом."""
    graph = get_compiled_graph()

    result = graph.invoke({"query": "", "norms": [], "cases": [], "trace": []})

    assert "answer" in result
    assert "trace" in result
