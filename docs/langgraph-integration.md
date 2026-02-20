# Интеграция LangGraph

## Версии и зависимости

```
LangGraph: 1.0.3
Установка: pip install langgraph
```

## Архитектура интеграции

Проект использует **LangGraph** как оркестратор для юридического RAG-агента.

### StateGraph (Наш граф)

```
┌──────────────────────────────────────────────────────────────┐
│                    StateGraph(AgentState)                     │
│                                                               │
│  START → classify_query → search_norms → search_cases        │
│                                              ↓                │
│  END ← verify_citation ← generate_answer ←─────────┘         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### AgentState (TypedDict)

```python
class AgentState(TypedDict, total=False):
    query: str                    # Исходный запрос
    law_type: Optional[str]       # Тип права
    norms: list[dict]             # Найденные нормы
    cases: list[dict]             # Найденные дела
    answer: str                   # Сгенерированный ответ
    trace: list[str]              # Пройденные узлы
    error: Optional[str]          # Ошибка (если есть)
```

## Соответствие лучшим практикам LangGraph

### ✅ Реализовано

| Практика | Реализация |
|----------|------------|
| **StateGraph с TypedDict** | `src/graph/state.py` |
| **Узлы как функции** | `src/graph/nodes.py` |
| **START/END из API** | `src/graph/workflow.py` |
| **Durable execution** | State передаётся между узлами |
| **Human-in-the-loop** | Дисклеймер в ответе |
| **Memory** | trace для аудита |
| **Debugging** | Логирование каждого узла |

### 📋 API LangGraph 1.0+

```python
from langgraph.graph import StateGraph, START, END

# Создание графа
workflow = StateGraph(AgentState)

# Добавление узлов
workflow.add_node("node_name", node_function)

# Определение потока
workflow.add_edge(START, "first_node")
workflow.add_edge("node_a", "node_b")
workflow.add_edge("last_node", END)

# Компиляция
graph = workflow.compile()

# Выполнение
result = graph.invoke(state)
```

## Отличия от примеров LangChain

| LangChain Example | Наш проект |
|-------------------|------------|
| Промпты через ChatPromptTemplate | Jinja2 шаблоны в `src/prompts/` |
| Векторное хранилище через LangChain | Прямой pgvector + psycopg2 |
| LLM через langchain.chat_models | Прямой httpx к OpenRouter API |
| Tools через @tool декоратор | Кастомные функции в `src/tools/` |

## Почему не используем абстракции LangChain

1. **Контроль над запросами**: Прямой httpx даёт полный контроль над retry/backoff
2. **Прозрачность**: Нет скрытых вызовов API
3. **Гибкость**: Легче кастомизировать под РФ-специфику
4. **Производительность**: Меньше накладных расходов

## Точки расширения

### 1. Добавление нового узла

```python
# src/graph/nodes.py
def new_node(state: AgentState) -> AgentState:
    logger.info("Node new_node: processing...")
    # Логика
    state["new_field"] = result
    state.setdefault("trace", []).append("new_node")
    return state

# src/graph/workflow.py
workflow.add_node("new_node", new_node)
workflow.add_edge("existing_node", "new_node")
```

### 2. Условные переходы

```python
from langgraph.graph import ConditionalEdges

def route(state: AgentState) -> str:
    if state["law_type"] == "арбитражное":
        return "search_arbitration"
    return "search_civil"

workflow.add_conditional_edges(
    "classify_query",
    route,
    {
        "search_arbitration": "search_arbitration",
        "search_civil": "search_civil",
    }
)
```

### 3. Human-in-the-loop (чекпоинты)

```python
from langgraph.checkpoint import MemorySaver

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# Пауза перед критическим узлом
config = {"configurable": {"thread_id": "user_123"}}
result = graph.invoke(state, config)
```

## Мониторинг и отладка

### LangSmith (опционально)

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
```

### Локальное логирование

```bash
# Включение debug-логов
export LOG_LEVEL=DEBUG

# Просмотр логов
tail -f logs/app.log
```

## Тестирование графа

```python
def test_graph_invoke():
    graph = get_compiled_graph()
    result = graph.invoke({
        "query": "Тест",
        "norms": [],
        "cases": [],
        "trace": []
    })
    assert "answer" in result
    assert len(result["trace"]) > 0
```

## Ресурсы

- [LangGraph Docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Reference](https://reference.langchain.com/python/langgraph/)
- [LangChain Academy](https://academy.langchain.com/courses/intro-to-langgraph)
- [GitHub](https://github.com/langchain-ai/langgraph)
