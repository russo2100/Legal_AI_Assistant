"""
Модуль узлов графа LangGraph.

Каждый узел — отдельная функция с явными input/output.
"""

import logging
from datetime import datetime
from typing import Any

from src.graph.state import AgentState

logger = logging.getLogger(__name__)


def classify_query(state: AgentState) -> AgentState:
    """
    Классифицирует юридический запрос по типу права.

    Args:
        state: Текущее состояние агента.

    Returns:
        Обновлённое состояние с определённым типом права.
    """
    logger.info(f"Node classify_query: input={state.get('query', '')}")

    query = state.get("query", "").lower()

    # Простая классификация по ключевым словам
    law_type = "гражданское"  # по умолчанию

    civil_keywords = ["гк", "гражданский кодекс", "договор", "обязательство", "собственность"]
    arbitration_keywords = ["апк", "арбитраж", "кад", "дело №", "а40-", "а41-", "а45-"]
    administrative_keywords = ["коап", "административный", "штраф", "нарушение"]
    procedural_keywords = ["гпк", "гражданский процесс", "иск", "судебный приказ"]

    if any(kw in query for kw in civil_keywords):
        law_type = "гражданское"
    elif any(kw in query for kw in arbitration_keywords):
        law_type = "арбитражное"
    elif any(kw in query for kw in administrative_keywords):
        law_type = "административное"
    elif any(kw in query for kw in procedural_keywords):
        law_type = "гражданский процесс"

    state["law_type"] = law_type
    state.setdefault("trace", []).append("classify_query")

    logger.info(f"Node classify_query: output law_type={law_type}")
    return state


def search_norms(state: AgentState) -> AgentState:
    """
    Ищет нормативные акты по запросу.

    Интеграция с src/rag/retriever.py

    Args:
        state: Текущее состояние агента.

    Returns:
        Обновлённое состояние с найденными нормами.
    """
    logger.info(f"Node search_norms: input query={state.get('query', '')}")

    query = state.get("query", "")
    law_type = state.get("law_type", "гражданское")

    norms: list[dict] = []

    try:
        from src.rag.retriever import get_retriever

        retriever = get_retriever()
        norms = retriever.retrieve(query=query, law_type=law_type)
        logger.info(f"Node search_norms: retrieved {len(norms)} norms from RAG")

    except Exception as e:
        # Fallback на заглушку при недоступности БД
        logger.warning(f"Node search_norms: RAG unavailable, using fallback ({e})")

        # Эмуляция поиска по кодексам
        if "330" in query and "гк" in query.lower():
            norms = [
                {
                    "title": "Гражданский кодекс РФ, Статья 330",
                    "text": "Неустойкой (штрафом, пеней) признается определенная законом или договором денежная сумма, которую должник обязан уплатить кредитору в случае неисполнения или ненадлежащего исполнения обязательства.",
                    "source": "ГК РФ Статья 330",
                    "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                }
            ]
        elif "договор" in query.lower():
            norms = [
                {
                    "title": "Гражданский кодекс РФ, Статья 420",
                    "text": "Договором признается соглашение двух или нескольких лиц об установлении, изменении или прекращении гражданских прав и обязанностей.",
                    "source": "ГК РФ Статья 420",
                    "url": "https://www.consultant.ru/document/cons_doc_LAW_5142/",
                }
            ]

    state["norms"] = norms
    state.setdefault("trace", []).append("search_norms")

    logger.info(f"Node search_norms: found {len(norms)} norms")
    return state


def search_cases(state: AgentState) -> AgentState:
    """
    Ищет судебную практику по запросу.

    Интеграция с src/tools/kad_parser.py

    Args:
        state: Текущее состояние агента.

    Returns:
        Обновлённое состояние с найденными делами.
    """
    logger.info(f"Node search_cases: input query={state.get('query', '')}")

    query = state.get("query", "")
    norms = state.get("norms", [])

    cases: list[dict] = []

    try:
        from src.tools.kad_parser import get_kad_parser

        parser = get_kad_parser()

        # Поиск по номерам статей из норм
        article_numbers = [n.get("article_number") for n in norms if n.get("article_number")]

        if article_numbers:
            # Ищем дела по номерам статей (максимум 3 запроса)
            for article_num in article_numbers[:3]:
                try:
                    found_cases = parser.search_cases(query=article_num, limit=2)
                    cases.extend(found_cases)
                except Exception as e:
                    logger.warning(f"Node search_cases: error searching article {article_num}: {e}")

        # Альтернатива: поиск по тексту запроса если не найдено дел
        if not cases:
            try:
                cases = parser.search_cases(query=query, limit=5)
            except Exception as e:
                logger.warning(f"Node search_cases: error searching query: {e}")

        logger.info(f"Node search_cases: found {len(cases)} cases from KAD parser")

    except Exception as e:
        # Fallback на заглушку при недоступности парсера
        logger.warning(f"Node search_cases: parser unavailable, using fallback ({e})")

        # Эмуляция поиска по kad.arbitr.ru
        if "неустойк" in query.lower() or "330" in query:
            cases = [
                {
                    "case_number": "А40-123456/2024",
                    "title": "ООО «Ромашка» v. ООО «Вектор»",
                    "summary": "Спор о взыскании неустойки по договору поставки. Суд удовлетворил требования частично.",
                    "url": "https://kad.arbitr.ru/Card/123456",
                    "date": "2024-10-15",
                }
            ]

    state["cases"] = cases
    state.setdefault("trace", []).append("search_cases")

    logger.info(f"Node search_cases: found {len(cases)} cases")
    return state


def generate_answer(state: AgentState) -> AgentState:
    """
    Генерирует ответ на основе найденных норм и практики.

    Интеграция с src/llm/client.py + src/llm/prompts.py

    Args:
        state: Текущее состояние агента.

    Returns:
        Обновлённое состояние с сгенерированным ответом.
    """
    logger.info(f"Node generate_answer: input norms={len(state.get('norms', []))}, cases={len(state.get('cases', []))}")

    query = state.get("query", "")
    norms = state.get("norms", [])
    cases = state.get("cases", [])
    law_type = state.get("law_type", "гражданское")

    answer = ""

    try:
        from src.llm.client import get_llm_client
        from src.llm.prompts import render_prompt

        client = get_llm_client()

        # Рендеринг промпта
        prompt = render_prompt(
            "generate",
            query=query,
            norms=norms,
            cases=cases,
            law_type=law_type,
        )

        # Генерация ответа через LLM
        response = client.generate(
            prompt=prompt,
            temperature=0.1,  # Детерминированный ответ
            max_tokens=2048,
        )

        answer = response.content
        logger.info(f"Node generate_answer: LLM response generated ({len(answer)} chars)")

    except Exception as e:
        # Fallback на шаблонный ответ при недоступности LLM
        logger.warning(f"Node generate_answer: LLM unavailable, using fallback ({e})")

        # Формирование ответа
        answer_parts: list[str] = []

        # Заголовок
        answer_parts.append(f"## Ответ по запросу: {query}\n")

        # Нормы
        if norms:
            answer_parts.append("### Normative base:\n")
            for norm in norms:
                answer_parts.append(f"- **{norm['title']}**\n")
                answer_parts.append(f"  {norm['text']}\n")
                answer_parts.append(f"  [Source]({norm['url']})\n\n")
        else:
            answer_parts.append("### Normative base:\n")
            answer_parts.append("No specific norms found for your request.\n\n")

        # Практика
        if cases:
            answer_parts.append("### Case law:\n")
            for case in cases:
                answer_parts.append(f"- **{case['case_number']}** ({case['title']})\n")
                answer_parts.append(f"  {case['summary']}\n")
                answer_parts.append(f"  [Case]({case['url']})\n\n")

        # Дисклеймер
        answer_parts.append("---\n")
        answer_parts.append("> **Disclaimer:** Analytical suggestion. Requires lawyer verification.\n")

        answer = "".join(answer_parts)

    state["answer"] = answer
    state.setdefault("trace", []).append("generate_answer")

    logger.info("Node generate_answer: answer generated")
    return state


def verify_citation(state: AgentState) -> AgentState:
    """
    Проверяет корректность цитирования источников.

    Интеграция с src/tools/citation_check.py

    Args:
        state: Текущее состояние агента.

    Returns:
        Обновлённое состояние с проверенным ответом.
    """
    logger.info("Node verify_citation: checking citations")

    answer = state.get("answer", "")
    norms = state.get("norms", [])
    cases = state.get("cases", [])

    try:
        from src.tools.citation_check import get_citation_checker

        checker = get_citation_checker()

        # Проверка и форматирование ответа с дисклеймером
        verified_answer = checker.verify_and_format(
            answer=answer,
            norms=norms,
            cases=cases,
            disclaimer="Аналитическая подсказка. Требуется проверка юристом.",
        )

        logger.info(f"Node verify_citation: citations verified ({len(verified_answer)} chars)")
        state["answer"] = verified_answer

    except Exception as e:
        # Fallback: добавляем дисклеймер вручную
        logger.warning(f"Node verify_citation: checker unavailable, using fallback ({e})")

        # Простая проверка: все ли источники имеют URL
        valid_norms = [n for n in norms if n.get("url")]
        valid_cases = [c for c in cases if c.get("url")]

        if len(valid_norms) != len(norms) or len(valid_cases) != len(cases):
            logger.warning("Node verify_citation: some citations missing URLs")

        # Добавляем дисклеймер к ответу
        if not answer.endswith("Требуется проверка юристом."):
            state["answer"] = answer + "\n\n---\n\n> ⚠️ **Дисклеймер:** Аналитическая подсказка. Требуется проверка юристом."

    state.setdefault("trace", []).append("verify_citation")

    logger.info("Node verify_citation: verification complete")
    return state
