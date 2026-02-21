"""
FastAPI сервер для Dashboard интерфейса.

Запуск:
    python -m src.api.server

API endpoints:
    POST /api/search - Поиск нормативных актов и судебных дел
    GET  /api/health - Проверка здоровья сервера
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Добавляем корень проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.utils.logging_config import setup_logging

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Инициализация FastAPI приложения
app = FastAPI(
    title="Юридический Ассистент API",
    description="API для поиска нормативных актов и судебной практики РФ",
    version="1.0.0",
)

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Модели данных
class SearchRequest(BaseModel):
    query: str = Field(..., description="Поисковый запрос", min_length=1)


class SearchResult(BaseModel):
    id: str
    title: str
    type: str  # 'norm' или 'case'
    description: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    number: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


class HealthResponse(BaseModel):
    status: str
    timestamp: str


# Временные данные для демонстрации (замените на реальный поиск через RAG)
MOCK_RESULTS = [
    SearchResult(
        id="1",
        title="Статья 330 ГК РФ - Понятие неустойки",
        type="norm",
        description="Неустойкой (штрафом, пеней) признается определенная законом или договором денежная сумма...",
        source="Гражданский кодекс РФ",
        date="2024-01-15",
        number="330",
    ),
    SearchResult(
        id="2",
        title="Статья 331 ГК РФ - Форма соглашения о неустойке",
        type="norm",
        description="Соглашение о неустойке должно быть совершено в письменной форме...",
        source="Гражданский кодекс РФ",
        date="2024-01-15",
        number="331",
    ),
    SearchResult(
        id="3",
        title="Дело А40-123456/2024",
        type="case",
        description="О взыскании неустойки по договору поставки. Требования удовлетворены частично...",
        source="Арбитражный суд г. Москвы",
        date="2024-06-20",
        number="А40-123456/2024",
    ),
    SearchResult(
        id="4",
        title="Дело А41-789012/2024",
        type="case",
        description="Спор о размере неустойки. Применена статья 333 ГК РФ...",
        source="Арбитражный суд Московской области",
        date="2024-08-10",
        number="А41-789012/2024",
    ),
]


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверка здоровья сервера."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/search", response_model=SearchResponse)
async def search_legal(request: SearchRequest) -> SearchResponse:
    """
    Поиск нормативных актов и судебных дел по запросу.
    
    В текущей реализации возвращает демонстрационные данные.
    В будущем будет интегрировано с RAG-системой и LangGraph.
    """
    logger.info(f"Search request: {request.query}")
    
    try:
        # Здесь будет вызов LangGraph workflow для реального поиска
        # graph = get_compiled_graph()
        # result = graph.invoke({"query": request.query, ...})
        
        # Пока возвращаем mock-данные с фильтрацией по запросу
        query_lower = request.query.lower()
        filtered_results = [
            r for r in MOCK_RESULTS
            if query_lower in r.title.lower() or 
               (r.description and query_lower in r.description.lower()) or
               (r.number and query_lower in r.number.lower())
        ]
        
        # Если ничего не найдено, возвращаем все результаты для демонстрации
        if not filtered_results:
            filtered_results = MOCK_RESULTS
        
        logger.info(f"Found {len(filtered_results)} results")
        
        return SearchResponse(results=filtered_results)
        
    except Exception as e:
        logger.exception(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "message": "Юридический Ассистент API",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
