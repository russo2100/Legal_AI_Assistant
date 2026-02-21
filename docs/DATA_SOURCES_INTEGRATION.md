# Интеграция источников данных для RAG

## Обзор

Система использует три основных источника данных:

1. **Нормативные акты** (ГК РФ, АПК РФ, ГПК РФ, КоАП РФ)
2. **Судебная практика** (kad.arbitr.ru)
3. **Альтернативные источники** (sudact.ru, rospravosudie.com)

---

## 1. Нормативные акты

### 1.1. Источники текстов кодексов

| Источник | URL | Формат | Актуальность |
|----------|-----|--------|--------------|
| Consultant.ru | https://www.consultant.ru/ | HTML/TXT | Ежедневно |
| Garant.ru | https://www.garant.ru/ | HTML/TXT | Ежедневно |
| Pravo.gov.ru | https://pravo.gov.ru/ | PDF/TXT | Официальный |

### 1.2. Загрузка кодексов

#### Вариант A: Ручная загрузка

```bash
# Перейдите на consultant.ru
# Найдите "Гражданский кодекс РФ"
# Скопируйте текст и сохраните в data/codes/GK.txt
```

#### Вариант B: Автоматическая загрузка (скрипт)

```python
# scripts/download_codes.py
import requests
from bs4 import BeautifulSoup

def download_gk_rf():
    """Скачивает ГК РФ с consultant.ru"""
    url = "https://www.consultant.ru/document/cons_doc_LAW_5142/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Извлечение текста
    text = soup.select_one(".body").get_text()
    
    # Сохранение
    with open("data/codes/GK.txt", "w", encoding="utf-8") as f:
        f.write(text)
```

### 1.3. Структура файла кодекса

```txt
ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ

Статья 1. Основные начала гражданского законодательства
1. Гражданское законодательство основывается на признании...

Статья 2. Отношения, регулируемые гражданским законодательством
1. Гражданское законодательство определяет правовое положение...
```

### 1.4. Индексация

```bash
# Полная индексация
python src/rag/indexer.py --codes data/codes

# Индексация конкретного кодекса
python src/rag/indexer.py --codes data/codes --type ГК
```

### 1.5. Обновление кодексов

```bash
# 1. Скачайте новую версию
# 2. Очистите БД
docker exec -it yurik-postgres psql -U postgres -d yurik_db -c "TRUNCATE chunks, codes CASCADE;"

# 3. Переиндексируйте
python src/rag/indexer.py --codes data/codes
```

---

## 2. Судебная практика (kad.arbitr.ru)

### 2.1. Интеграция через парсер

Файл: `src/tools/kad_parser.py`

```python
from src.tools.kad_parser import KadParser

async def search():
    parser = KadParser(rate_limit=2.0)
    
    # Поиск по номеру дела
    cases = await parser.search_cases("А40-123456/2024")
    
    # Текстовый поиск
    cases = await parser.search_cases("неустойка по договору подряда")
    
    await parser.close()
```

### 2.2. Rate limiting

```python
# В .env:
KAD_RATE_LIMIT=0.5  # 2 секунды между запросами

# В коде:
parser = KadParser(rate_limit=2.0)  # 2 секунды
```

### 2.3. Обход блокировок

Если kad.arbitr.ru блокирует запросы:

```python
# Использование proxy
parser = KadParser(
    base_url="https://kad.arbitr.ru",
    proxies={"http": "http://proxy:8080", "https": "http://proxy:8080"}
)
```

### 2.4. Парсинг карточки дела

```python
async def get_case_details(case_number: str):
    parser = KadParser()
    cases = await parser.search_cases(case_number)
    
    if cases:
        case = cases[0]
        print(f"Дело: {case.case_number}")
        print(f"Суд: {case.court}")
        print(f"Стороны: {case.parties}")
        print(f"Решение: {case.summary}")
```

---

## 3. Альтернативные источники

### 3.1. Sudact.ru

```python
# scripts/sudact_parser.py
import httpx
from bs4 import BeautifulSoup

async def search_sudact(query: str):
    url = "https://sudact.ru/regular/doc/"
    params = {"regular": query}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        soup = BeautifulSoup(response.text, 'lxml')
        
        results = []
        for item in soup.select(".law-doc"):
            results.append({
                "title": item.select_one(".doc-name").text.strip(),
                "url": item.select_one("a")["href"],
                "date": item.select_one(".doc-date").text.strip(),
            })
        
        return results
```

### 3.2. RosPravoSud

```python
# scripts/rospravosud_parser.py
async def search_rospravosud(query: str):
    url = "https://rospravosudie.com/"
    params = {"query": query}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        # Парсинг аналогично sudact
```

---

## 4. Fallback-логика

### 4.1. Приоритет источников

```python
SOURCES_PRIORITY = [
    "kad.arbitr.ru",      # Основной
    "sudact.ru",          # Fallback 1
    "rospravosudie.com",  # Fallback 2
]
```

### 4.2. Реализация в nodes.py

```python
def search_cases(state: AgentState) -> AgentState:
    cases = []
    
    # Попытка 1: kad.arbitr.ru
    try:
        cases = parser.search_cases(query)
        if cases:
            return {"cases": cases}
    except Exception:
        pass
    
    # Fallback 1: sudact.ru
    try:
        cases = search_sudact(query)
        if cases:
            return {"cases": cases}
    except Exception:
        pass
    
    # Fallback 2: rospravosudie.com
    try:
        cases = search_rospravosud(query)
    except Exception:
        pass
    
    return {"cases": []}
```

---

## 5. Кэширование результатов

### 5.1. Redis кэш

```python
# scripts/cache.py
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_search_result(query: str, result: list, ttl: int = 3600):
    """Кэширует результат поиска на 1 час"""
    key = f"search:{query}"
    redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))

def get_cached_result(query: str) -> list | None:
    """Получает кэшированный результат"""
    result = redis_client.get(f"search:{query}")
    return json.loads(result) if result else None
```

### 5.2. Добавление кэша в парсер

```python
class KadParser:
    async def search_cases(self, query: str):
        # Проверка кэша
        cached = get_cached_result(query)
        if cached:
            return cached
        
        # Поиск
        results = await self._search(query)
        
        # Кэширование
        cache_search_result(query, results)
        return results
```

---

## 6. Мониторинг источников

### 6.1. Проверка доступности

```python
# scripts/check_sources.py
import httpx

async def check_source(url: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

async def main():
    sources = {
        "kad.arbitr.ru": "https://kad.arbitr.ru/",
        "sudact.ru": "https://sudact.ru/",
        "consultant.ru": "https://www.consultant.ru/",
    }
    
    for name, url in sources.items():
        status = await check_source(url)
        print(f"{'✅' if status else '❌'} {name}")
```

### 6.2. Логирование ошибок

```python
# В .env:
LOG_LEVEL=DEBUG

# Просмотр ошибок:
Get-Content logs\app.log | Select-String "ERROR"
```

---

## 7. API для внешних источников

### 7.1. Интеграция с API Consultant.ru

```python
# При наличии API-ключа
class ConsultantAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.consultant.ru/"
    
    def search_norm(self, query: str):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(
            f"{self.base_url}search",
            headers=headers,
            params={"query": query}
        )
        return response.json()
```

---

## 8. Обновление данных

### 8.1. Расписание обновлений

```bash
# Crontab для Linux или Task Scheduler для Windows
# Ежедневное обновление
0 2 * * * cd /path/to/yurik && python scripts/download_codes.py
0 3 * * * cd /path/to/yurik && python src/rag/indexer.py --codes data/codes
```

### 8.2. Автоматическая проверка обновлений

```python
# scripts/check_updates.py
def check_code_updates():
    """Проверяет обновления кодексов"""
    current_version = get_local_version("GK.txt")
    latest_version = get_remote_version("consultant.ru")
    
    if current_version < latest_version:
        download_new_version()
        reindex()
```

---

## 9. Примеры использования

### 9.1. Поиск нормы с кэшированием

```python
from src.rag.retriever import get_retriever
from scripts.cache import get_cached_result, cache_search_result

def search_norm_cached(query: str):
    cached = get_cached_result(query)
    if cached:
        return cached
    
    retriever = get_retriever()
    results = retriever.retrieve(query)
    
    cache_search_result(query, results)
    return results
```

### 9.2. Комплексный поиск

```python
async def comprehensive_search(query: str):
    """Ищет нормы и практику из всех источников"""
    results = {
        "norms": [],
        "cases": [],
        "sources_used": []
    }
    
    # Нормы
    retriever = get_retriever()
    results["norms"] = retriever.retrieve(query)
    results["sources_used"].append("local_db")
    
    # Практика
    parser = KadParser()
    cases = await parser.search_cases(query)
    if cases:
        results["cases"].extend(cases)
        results["sources_used"].append("kad.arbitr.ru")
    
    return results
```

---

## 10. Контакты источников

| Источник | Поддержка | API | Документация |
|----------|-----------|-----|--------------|
| Consultant.ru | support@consultant.ru | ✅ | https://www.consultant.ru/api/ |
| Garant.ru | info@garant.ru | ❌ | - |
| kad.arbitr.ru | tech@kad.arbitr.ru | ❌ | - |
| Sudact.ru | support@sudact.ru | ❌ | - |
