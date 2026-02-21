# Yurik Dashboard - Веб-интерфейс

Веб-интерфейс для юридического RAG-агента на React + TypeScript.

## Быстрый старт

### 1. Установка зависимостей

```bash
cd frontend
npm install
```

### 2. Запуск сервера разработки

```bash
npm run dev
```

Сервер запустится на `http://localhost:3000`

### 3. Запуск бэкенда API

В корневой директории проекта:

```bash
# Установка зависимостей (если еще не установлены)
pip install -r requirements.txt

# Запуск API сервера
python -m src.api.server
```

API сервер запустится на `http://localhost:8000`

## Структура проекта

```
frontend/
├── src/
│   ├── api/           # API клиенты
│   ├── components/    # React компоненты
│   │   ├── Header.tsx
│   │   ├── QueryInput.tsx
│   │   ├── Sidebar.tsx
│   │   ├── ResultsList.tsx
│   │   └── ResultDetail.tsx
│   ├── hooks/         # Кастомные хуки
│   │   ├── useSearchResults.ts
│   │   └── useSearchHistory.ts
│   ├── pages/         # Страницы приложения
│   │   ├── Home.tsx
│   │   ├── DocumentDraft.tsx
│   │   └── CaseSearch.tsx
│   ├── App.tsx        # Корневой компонент
│   ├── main.tsx       # Точка входа
│   └── index.css      # Глобальные стили
├── index.html
├── package.json
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
└── vite.config.ts
```

## Технологии

- **React 18** - UI библиотека
- **TypeScript** - Типизация
- **Vite** - Сборщик
- **Material-UI** - Компоненты
- **Tailwind CSS** - Утилитарные стили
- **React Router** - Маршрутизация

## Сборка для продакшена

```bash
npm run build
```

Собранные файлы появятся в папке `dist/`

## Тестирование

```bash
npm run test
```

## Линтинг

```bash
npm run lint
```

## Интеграция с бэкендом

Фронтенд настроен на проксирование запросов `/api` на бэкенд сервер (`http://localhost:8000`).

Настройка находится в `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## Доступные API endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/search` | POST | Поиск нормативных актов и дел |
| `/api/health` | GET | Проверка здоровья сервера |

### Пример запроса на поиск

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Статья 330 ГК РФ"}'
```
