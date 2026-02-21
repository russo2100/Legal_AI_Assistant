# Инструкция по запуску Dashboard

## Предварительные требования

- Python 3.11+
- Node.js 18+
- npm или yarn

## Шаг 1: Установка зависимостей бэкенда

```bash
# В корневой директории проекта
python -m venv venv
.\venv\Scripts\Activate.ps1  # PowerShell
# или
.\venv\Scripts\activate.bat  # CMD

pip install -r requirements.txt
```

## Шаг 2: Установка зависимостей фронтенда

```bash
# В папке frontend
cd frontend
npm install
```

> ⚠️ **Примечание:** Если возникает ошибка сети, попробуйте:
> - Проверить подключение к интернету
> - Использовать VPN
> - Очистить кэш npm: `npm cache clean --force`

## Шаг 3: Настройка окружения

```bash
# В корневой директории
Copy-Item .env.example .env

# Отредактируйте .env и добавьте необходимые API-ключи
```

## Шаг 4: Запуск приложения

### Терминал 1: Бэкенд (FastAPI)

```bash
# В корневой директории (с активированным venv)
python -m src.api.server
```

Сервер запустится на `http://localhost:8000`
API документация: `http://localhost:8000/docs`

### Терминал 2: Фронтенд (Vite + React)

```bash
# В папке frontend
npm run dev
```

Приложение откроется на `http://localhost:3000`

## Шаг 5: Проверка работы

1. Откройте браузер: `http://localhost:3000`
2. Введите поисковый запрос (например, "Статья 330 ГК РФ")
3. Нажмите "Поиск" или Enter
4. Выберите результат из списка для просмотра деталей

## Тестирование API

### Через браузер
Откройте `http://localhost:8000/docs` для Swagger UI

### Через curl
```bash
# Проверка здоровья
curl http://localhost:8000/api/health

# Поисковый запрос
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Статья 330 ГК РФ\"}"
```

## Возможные проблемы

### Ошибка CORS
Убедитесь, что бэкенд запущен на порту 8000, а фронтенд на 3000.

### Ошибка npm install
Попробуйте:
```bash
npm cache clean --force
npm install --legacy-peer-deps
```

### Порт занят
Измените порт в `vite.config.ts` или `src/api/server.py`

## Сборка для продакшена

```bash
# Фронтенд
cd frontend
npm run build

# Собранные файлы будут в папке dist/
```

## Дополнительная документация

- [README проекта](../README.md)
- [Документация фронтенда](./README.md)
