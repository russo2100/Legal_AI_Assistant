"""
E2E-тесты на golden set.
"""

import json
import pytest
from pathlib import Path

from src.graph.workflow import get_compiled_graph


def load_golden_set() -> list[dict]:
    """Загружает golden set из файла."""
    golden_file = Path(__file__).parent / "golden_set.jsonl"
    cases = []
    with open(golden_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases


@pytest.fixture
def graph():
    """Фикстура с графом."""
    return get_compiled_graph()


@pytest.mark.parametrize("case", load_golden_set(), ids=lambda c: c["query"][:30])
def test_golden_case(graph, case):
    """Тест кейса из golden set."""
    result = graph.invoke({
        "query": case["query"],
        "norms": [],
        "cases": [],
        "trace": [],
    })

    # Проверка типа права
    assert result["law_type"] == case["expected_law_type"], f"Неверный тип права для: {case['query']}"

    # Проверка trace
    assert len(result["trace"]) > 0, "Trace пуст"

    # Проверка наличия ответа
    assert "answer" in result, "Нет ответа"
    assert len(result["answer"]) > 0, "Пустой ответ"


def test_golden_set_completeness():
    """Тест полноты golden set."""
    cases = load_golden_set()
    assert len(cases) >= 10, "Golden set должен содержать минимум 10 кейсов"

    # Проверка структуры каждого кейса
    for case in cases:
        assert "query" in case, "Отсутствует query"
        assert "expected_law_type" in case, "Отсутствует expected_law_type"
