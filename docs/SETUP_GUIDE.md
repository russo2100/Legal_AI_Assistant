# Руководство по настройке RAG для юридического агента

## 1. Настройка Docker с PostgreSQL/pgvector

### Шаг 1.1: Запуск Docker Desktop

1. Откройте **Docker Desktop** (иконка в трее или через меню Пуск)
2. Дождитесь полной загрузки (статус "Docker Desktop is running")
3. Проверьте работу командой:
   ```bash
   docker --version
   docker ps
   ```

### Шаг 1.2: Запуск PostgreSQL с pgvector

```bash
# Перейдите в директорию проекта
cd c:\Users\Руслан\Desktop\Python\yurik

# Запустите Docker Compose
docker compose -f docker/docker-compose.yml up -d

# Проверьте статус контейнеров
docker compose ps
```

Ожидаемый вывод:
```
NAME                 STATUS         PORTS
yurik-postgres       Up (healthy)   0.0.0.0:5432->5432/tcp
```

### Шаг 1.3: Проверка подключения к БД

```bash
# Подключение к PostgreSQL
docker exec -it yurik-postgres psql -U postgres -d yurik_db

# В SQL-консоли проверьте расширение pgvector:
\dx

# Должно отобразиться:
#  Name   | Version |   Schema   |         Description          
# --------+---------+------------+------------------------------
#  vector | 0.7.2   | public     | vector data type and ivfflat index for similarity search
```

### Шаг 1.4: Устранение проблем

**Проблема: Docker Desktop не запускается**
- Решение: Перезапустите компьютер и попробуйте снова
- Альтернатива: Используйте WSL2 backend для Docker Desktop

**Проблема: Контейнер не стартует**
```bash
# Посмотрите логи
docker compose logs postgres

# Пересоздайте контейнер
docker compose down
docker compose up -d --force-recreate
```

---

## 2. Индексация кодексов

### Шаг 2.1: Подготовка текстов кодексов

Тексты кодексов уже находятся в `data/codes/`:
- `GK.txt` — Гражданский кодекс РФ
- `APK.txt` — Арбитражный процессуальный кодекс РФ

**При необходимости добавьте другие кодексы:**

1. Скачайте тексты с официальных источников:
   - [Consultant.ru](https://www.consultant.ru/)
   - [Garant.ru](https://www.garant.ru/)
   - [Pravo.gov.ru](https://pravo.gov.ru/)

2. Сохраните в `data/codes/`:
   ```
   data/codes/
   ├── GK.txt       # Гражданский кодекс
   ├── APK.txt      # Арбитражный процессуальный кодекс
   ├── GPK.txt      # Гражданский процессуальный кодекс
   └── KoAP.txt     # Кодекс об административных правонарушениях
   ```

### Шаг 2.2: Запуск индексации

```bash
# Активируйте виртуальное окружение
.\venv\Scripts\Activate.ps1  # PowerShell
# или
.\venv\Scripts\activate.bat  # CMD

# Запустите индексатор
python src/rag/indexer.py --codes data/codes
```

Ожидаемый вывод:
```
INFO:src.rag.indexer:Подключение к PostgreSQL установлено, pgvector зарегистрирован
INFO:src.rag.indexer:Таблицы созданы, индексы построены
INFO:src.rag.indexer:Индексация файла: data/codes/GK.txt
INFO:src.rag.indexer:Разбито на 350 чанков
INFO:src.rag.indexer:Проиндексировано 350 чанков из ГК
INFO:src.rag.indexer:Индексация файла: data/codes/APK.txt
INFO:src.rag.indexer:Разбито на 180 чанков
INFO:src.rag.indexer:Проиндексировано 180 чанков из АПК
✅ Проиндексировано 530 чанков
```

### Шаг 2.3: Проверка индексации

```bash
# Подключитесь к БД
docker exec -it yurik-postgres psql -U postgres -d yurik_db

# Проверьте количество кодексов
SELECT COUNT(*) FROM codes;

# Проверьте количество чанков
SELECT COUNT(*) FROM chunks;

# Проверьте индекс
SELECT * FROM chunks LIMIT 5;
```

---

## 3. Тестирование RAG-поиска

### Шаг 3.1: Тестовый запрос через CLI

```bash
python -m src.main "Статья 330 ГК РФ неустойка"
```

Ожидаемый результат:
- ✅ Классификация запроса: гражданское право
- ✅ Поиск норм: найдена ст. 330 ГК РФ
- ✅ Поиск практики: дела из kad.arbitr.ru
- ✅ Генерация ответа через LLM
- ✅ Проверка цитирования

### Шаг 3.2: Проверка логов

```bash
# Логи приложения
type logs\app.log

# Или в реальном времени (PowerShell)
Get-Content logs\app.log -Wait -Tail 50
```

### Шаг 3.3: E2E тесты

```bash
# Запуск всех тестов
pytest src/tests/test_e2e.py -v

# Запуск конкретного теста
pytest src/tests/test_e2e.py::test_golden_case[Статья 330 ГК РФ неустойка] -v
```

---

## 4. Интеграция с kad.arbitr.ru

### Шаг 4.1: Тестирование парсера

```python
import asyncio
from src.tools.kad_parser import KadParser

async def test_parser():
    parser = KadParser(rate_limit=2.0)
    
    # Поиск по номеру дела
    cases = await parser.search_cases("А40-123456/2024")
    print(f"Найдено дел: {len(cases)}")
    
    # Текстовый поиск
    cases = await parser.search_cases("неустойка по договору подряда")
    print(f"Найдено дел: {len(cases)}")
    
    await parser.close()

asyncio.run(test_parser())
```

### Шаг 4.2: Rate limiting

В `.env` установлен параметр:
```
KAD_RATE_LIMIT=0.5
```

Это означает задержку 2 секунды между запросами для избежания блокировки.

### Шаг 4.3: Fallback-логика

Если `kad.arbitr.ru` недоступен, система автоматически переключается на альтернативные источники:
- [Sudact.ru](https://sudact.ru/)
- [RosPravoSud](https://rospravosudie.com/)

---

## 5. Дополнительные улучшения

### 5.1: Кэширование с Redis

```bash
# Установка Redis
pip install redis

# Добавление в docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 5.2: Мониторинг

```bash
# Проверка состояния БД
docker exec yurik-postgres pg_isready -U postgres

# Проверка размера БД
docker exec yurik-postgres psql -U postgres -d yurik_db -c "SELECT pg_size_pretty(pg_database_size('yurik_db'));"
```

---

## 6. Решение проблем

### Ошибка: "DATABASE_URL не установлен"
**Решение:** Проверьте `.env` файл:
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yurik_db
```

### Ошибка: "Connection refused"
**Решение:** Убедитесь, что Docker запущен:
```bash
docker compose ps
```

### Ошибка: "OPENROUTER_API_KEY не установлен"
**Решение:** Получите ключ на [openrouter.ai](https://openrouter.ai/keys) и добавьте в `.env`

### Ошибка индексации: "Permission denied"
**Решение:** Запустите терминал от имени администратора

---

## 7. Полный цикл тестирования

```bash
# 1. Запуск Docker
docker compose up -d

# 2. Индексация кодексов
python src/rag/indexer.py --codes data/codes

# 3. Тестовый запрос
python -m src.main "Статья 330 ГК РФ неустойка"

# 4. E2E тесты
pytest src/tests/test_e2e.py -v

# 5. Проверка логов
Get-Content logs\app.log -Tail 100
```

---

## 8. Контакты и поддержка

- Документация: `docs/`
- Логи ошибок: `logs/app.log`
- Progress: `docs/progress.md`
