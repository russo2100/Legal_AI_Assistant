"""
Модуль определения состояния агента (AgentState).

Используется LangGraph для передачи данных между узлами графа.
"""

from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    """
    Состояние юридического RAG-агента.

    Attributes:
        query: Исходный запрос пользователя.
        law_type: Тип права (гражданское, арбитражное, административное и т.д.).
        norms: Список найденных нормативных актов.
        cases: Список найденных судебных дел.
        answer: Сгенерированный ответ.
        trace: Список пройденных узлов графа для трассировки.
        error: Сообщение об ошибке (если возникла).
    """

    query: str
    law_type: Optional[str]
    norms: list[dict]
    cases: list[dict]
    answer: str
    trace: list[str]
    error: Optional[str]
