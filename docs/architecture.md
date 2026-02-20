# Архитектура Legal AI Assistant

## Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        Пользователь                              │
│                    (CLI запрос)                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      main.py                                     │
│              (Точка входа, логирование)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Workflow                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  classify_   │→ │  search_     │→ │  search_     │          │
│  │   query      │  │   norms      │  │   cases      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                                    │                  │
│         └────────────────┬───────────────────┘                  │
│                          ▼                                      │
│                   ┌──────────────┐  ┌──────────────┐           │
│                   │   generate_  │→ │   verify_    │           │
│                   │   answer     │  │  citation    │           │
│                   └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Внешние сервисы                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  OpenRouter │  │  PostgreSQL │  │ kad.arbitr. │             │
│  │  (LLM +     │  │  + pgvector │  │     ru      │             │
│  │  Embeddings)│  │  (RAG)      │  │  (Парсер)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Graph (LangGraph)

**Файлы:** `src/graph/state.py`, `nodes.py`, `workflow.py`

| Узел | Вход | Выход | Описание |
|------|------|-------|----------|
| `classify_query` | query | law_type | Классификация по типу права |
| `search_norms` | query, law_type | norms | RAG-поиск по кодексам |
| `search_cases` | query | cases | Поиск в kad.arbitr.ru |
| `generate_answer` | norms, cases | answer | Генерация через LLM |
| `verify_citation` | answer, norms, cases | verified_answer | Проверка ссылок |

### 2. RAG (Retrieval-Augmented Generation)

**Файлы:** `src/rag/embeddings.py`, `indexer.py`, `retriever.py`

```
Кодексы (txt) → Chunking → Embeddings → pgvector
                      ↓
Запрос → Embedding → Hybrid Search (BM25 + Vector) → Rerank → Нормы
```

### 3. Tools

**Файлы:** `src/tools/kad_parser.py`, `citation_check.py`, `legal_utils.py`

- **KadParser**: Асинхронный парсинг kad.arbitr.ru
- **CitationChecker**: Валидация ссылок в ответе
- **LegalUtils**: Вспомогательные функции (расчёт неустойки, сроки давности)

### 4. LLM

**Файлы:** `src/llm/client.py`, `prompts.py`

- **OpenRouterClient**: Обёртка над API с retry/backoff
- **PromptLoader**: Jinja2 шаблоны для генерации

## Поток данных

```
1. Пользователь → query → classify_query
2. classify_query → law_type → search_norms
3. search_norms → norms → search_cases
4. search_cases → cases → generate_answer
5. generate_answer → answer → verify_citation
6. verify_citation → final_answer → Пользователь
```

## State Schema

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

## Безопасность

- API-ключи через `.env` (не коммитить)
- Rate limiting для внешних запросов
- Санитизация входных данных (prompt-injection)
- Логирование всех запросов (аудит)

## Масштабирование

```
Локально (dev)          VPS (prod)
├── venv                ├── Docker
├── PostgreSQL local    ├── PostgreSQL + pgvector
└── OpenRouter API      ├── nginx (reverse proxy)
                        └── systemd / supervisor
```
