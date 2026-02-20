-- Инициализация PostgreSQL для Legal RAG Agent

-- Включаем расширение pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Создаём пользователя (если не создан через env)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'postgres';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE yurik_db TO postgres;

-- Сообщение об успехе
SELECT 'Database initialized successfully!' AS status;
