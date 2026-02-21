# Fallback-система для LLM-провайдеров

## Обзор

Система обеспечивает отказоустойчивость за счёт использования нескольких LLM-провайдеров:
- **Основной**: OpenRouter (модель: `arcee-ai/trinity-large-preview:free` или `qwen/qwen-2.5-72b-instruct`)
- **Fallback**: Perplexity (модель: `sonar-large-online`)

При недоступности основного провайдера система автоматически переключается на fallback.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                   MultiLLMClient                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐      ┌──────────────────────┐    │
│  │ OpenRouterClient│ ────▶│   Попытка запроса    │    │
│  │   (Primary)     │      │                        │    │
│  └─────────────────┘      └──────────────────────┘    │
│                            │                          │
│                            ▼ Ошибка                   │
│                    ┌──────────────────┐               │
│                    │ PerplexityClient │               │
│                    │   (Fallback)     │               │
│                    └──────────────────┘               │
│                            │                          │
│                            ▼ Успех                    │
│                    ┌──────────────────┐               │
│                    │  LLMResponse     │               │
│                    │  provider=...    │               │
│                    └──────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## Конфигурация

### Переменные окружения

```bash
# ===========================================
# LLM Провайдеры (с fallback-логикой)
# ===========================================

# Primary LLM provider (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=arcee-ai/trinity-large-preview:free
OPENROUTER_RATE_LIMIT=0.5

# Fallback LLM provider (Perplexity)
PERPLEXITY_API_KEY=pplx-...
PERPLEXITY_MODEL=sonar-large-online
PERPLEXITY_RATE_LIMIT=0.5
```

### Файлы

| Файл | Описание |
|------|----------|
| `src/llm/client.py` | Основной клиент с fallback-логикой |
| `src/llm/perplexity_client.py` | Клиент для Perplexity API |
| `src/llm/__init__.py` | Экспорт компонентов |
| `src/tests/test_llm_fallback.py` | Тесты fallback-логики |
| `.env.example` | Шаблон конфигурации |

---

## Использование

### Базовый пример

```python
from src.llm import get_llm_client

# Получаем клиент с автоматическим fallback
client = get_llm_client()

# Генерируем ответ (автоматически переключится на fallback при ошибке)
response = client.generate("Какой закон регулирует неустойку?")

print(f"Ответ: {response.content}")
print(f"Провайдер: {response.provider}")  # "openrouter" или "perplexity"
```

### Отключение fallback

```python
# Использовать только основной провайдер
response = client.generate(
    "Ваш запрос",
    use_fallback=False  # Выбросит ошибку если OpenRouter недоступен
)
```

### Генерация JSON

```python
# Генерация JSON с автоматическим fallback
data = client.generate_json(
    "Извлеки данные из текста",
    system_prompt="Ты JSON API"
)
```

---

## Логирование

Система логирует все попытки и переключения:

```
INFO     src.llm.client:client.py:273 Попытка использования OpenRouter...
WARNING  src.llm.client:client.py:276 OpenRouter недоступен: Timeout error
INFO     src.llm.client:client.py:283 Переключение на Perplexity (fallback)...
INFO     src.llm.perplexity_client:perplexity_client.py:156 Perplexity ответ: 250 символов
```

---

## Обработка ошибок

### Сценарий 1: OpenRouter доступен
```
✅ Запрос → OpenRouter → Успех
```

### Сценарий 2: OpenRouter недоступен, Perplexity доступен
```
❌ Запрос → OpenRouter → Ошибка
✅ Переключение → Perplexity → Успех
```

### Сценарий 3: Оба провайдера недоступны
```
❌ Запрос → OpenRouter → Ошибка
❌ Переключение → Perplexity → Ошибка
❌ RuntimeError: "Все LLM-провайдеры недоступны"
```

---

## Тестирование

### Запуск тестов

```bash
# Все тесты fallback-логики
pytest src/tests/test_llm_fallback.py -v

# Конкретный тест
pytest src/tests/test_llm_fallback.py::TestMultiLLMClient::test_generate_fallback_on_primary_failure -v
```

### Покрытие тестов

| Тест | Описание |
|------|----------|
| `test_generate_primary_success` | Успешный запрос к основному провайдеру |
| `test_generate_fallback_on_primary_failure` | Переключение на fallback при ошибке |
| `test_generate_all_providers_fail` | Ошибка когда все провайдеры недоступны |
| `test_generate_json_success` | Генерация JSON |
| `test_fallback_logging` | Проверка логирования |
| `test_use_fallback_flag` | Отключение fallback флагом |

---

## Rate Limiting

Для каждого провайдера настроено ограничение частоты запросов:

```python
# В client.py
self._rate_limit = float(os.getenv("OPENROUTER_RATE_LIMIT", "2.0"))

# В perplexity_client.py
self._rate_limit = float(os.getenv("PERPLEXITY_RATE_LIMIT", "0.5"))
```

Это предотвращает превышение лимитов API.

---

## Расширение: Добавление нового провайдера

### Шаг 1: Создать класс клиента

```python
# src/llm/new_provider_client.py
class NewProviderClient:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("NEW_PROVIDER_API_KEY")
        self.model = model or os.getenv("NEW_PROVIDER_MODEL")
    
    def generate(self, prompt, **kwargs):
        # Реализация запроса
        pass
```

### Шаг 2: Обновить MultiLLMClient

```python
class MultiLLMClient:
    def __init__(self):
        self.primary_client = OpenRouterClient(...)
        self.fallback_client = PerplexityClient(...)
        self.secondary_fallback = NewProviderClient(...)  # Новый провайдер
    
    def generate(self, prompt, **kwargs):
        try:
            return self.primary_client.generate(prompt, **kwargs)
        except Exception as e:
            try:
                return self.fallback_client.generate(prompt, **kwargs)
            except Exception:
                # Третий уровень fallback
                return self.secondary_fallback.generate(prompt, **kwargs)
```

---

## Рекомендации

### ✅ Делать

1. Всегда устанавливайте оба API-ключа для отказоустойчивости
2. Проверяйте `response.provider` для понимания какой провайдер ответил
3. Логируйте ошибки для анализа доступности провайдеров
4. Настройте rate limiting согласно лимитам API

### ❌ Не делать

1. Не полагайтесь только на одного провайдера в продакшене
2. Не игнорируйте логи переключения на fallback
3. Не устанавливайте rate limit выше рекомендованного API

---

## Мониторинг

### Метрики для отслеживания

1. **Success Rate по провайдерам**
   ```
   OpenRouter: 95% запросов успешны
   Perplexity: 5% запросов (fallback)
   ```

2. **Среднее время ответа**
   ```
   OpenRouter: 2.5s
   Perplexity: 1.8s
   ```

3. **Частота переключений на fallback**
   ```
   Fallback срабатывает в 5% случаев
   ```

---

## Troubleshooting

### Проблема: "PERPLEXITY_API_KEY не установлен"

**Решение:** Добавьте в `.env`:
```bash
PERPLEXITY_API_KEY=pplx-...
```

### Проблема: Частые переключения на fallback

**Возможные причины:**
1. Превышен лимит запросов OpenRouter
2. Проблемы с сетью до серверов OpenRouter
3. Неверный API-ключ

**Решение:**
1. Проверьте логи на предмет rate limit ошибок
2. Проверьте доступность API OpenRouter
3. Обновите API-ключ

### Проблема: Таймауты запросов

**Решение:** Увеличьте таймаут в клиенте:
```python
self._client = httpx.Client(
    timeout=httpx.Timeout(120.0),  # Увеличить с 60 до 120 секунд
    ...
)
```

---

## См. также

- [OpenRouter API Docs](https://openrouter.ai/docs)
- [Perplexity API Docs](https://docs.perplexity.ai/)
- [Tenacity Docs](https://tenacity.readthedocs.io/) (retry logic)
- [HTTPX Docs](https://www.python-httpx.org/)
