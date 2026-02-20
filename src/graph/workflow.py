"""
Модуль сборки графа LangGraph.

Определяет workflow: START → classify → norms → cases → generate → verify → END
"""

import logging

from langgraph.graph import StateGraph, START, END

from src.graph.state import AgentState
from src.graph.nodes import (
    classify_query,
    search_norms,
    search_cases,
    generate_answer,
    verify_citation,
)

logger = logging.getLogger(__name__)


def build_workflow() -> StateGraph:
    """
    Строит граф выполнения для юридического агента.

    Returns:
        StateGraph: собранный граф LangGraph.
    """
    logger.info("Building LangGraph workflow...")

    # Создаём граф
    workflow = StateGraph(AgentState)

    # Добавляем узлы
    workflow.add_node("classify_query", classify_query)
    workflow.add_node("search_norms", search_norms)
    workflow.add_node("search_cases", search_cases)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("verify_citation", verify_citation)

    # Определяем поток выполнения (используем START из нового API)
    workflow.add_edge(START, "classify_query")
    workflow.add_edge("classify_query", "search_norms")
    workflow.add_edge("search_norms", "search_cases")
    workflow.add_edge("search_cases", "generate_answer")
    workflow.add_edge("generate_answer", "verify_citation")
    workflow.add_edge("verify_citation", END)

    logger.info("LangGraph workflow built successfully")
    return workflow


def get_compiled_graph():
    """
    Возвращает скомпилированный граф.

    Returns:
        CompiledStateGraph: готовый к выполнению граф.
    """
    return build_workflow().compile()
