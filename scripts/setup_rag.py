"""
Скрипт проверки и индексации кодексов.

Автоматически:
1. Проверяет наличие Docker и БД
2. Проверяет тексты кодексов
3. Запускает индексацию
"""

import os
import sys
import subprocess
from pathlib import Path


def check_docker() -> bool:
    """Проверяет доступность Docker."""
    print("🔍 Проверка Docker...")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(f"✅ {result.stdout.strip()}")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Docker не найден. Установите Docker Desktop.")
        return False


def check_docker_running() -> bool:
    """Проверяет запущен ли Docker Desktop."""
    print("🔍 Проверка статуса Docker...")
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✅ Docker запущен")
            return True
        else:
            print("❌ Docker не отвечает. Запустите Docker Desktop.")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def check_postgres() -> bool:
    """Проверяет запущен ли PostgreSQL."""
    print("🔍 Проверка PostgreSQL...")
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "ps"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "yurik-postgres" in result.stdout and "Up" in result.stdout:
            print("✅ PostgreSQL запущен")
            return True
        else:
            print("⚠️ PostgreSQL не запущен")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def start_docker() -> bool:
    """Запускает Docker Compose."""
    print("🚀 Запуск Docker Compose...")
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "up", "-d"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("✅ Docker Compose запущен")
            return True
        else:
            print(f"❌ Ошибка запуска: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def check_codes() -> dict:
    """Проверяет наличие текстов кодексов."""
    print("🔍 Проверка текстов кодексов...")
    codes_dir = Path("data/codes")
    expected_codes = {
        "GK.txt": "Гражданский кодекс",
        "APK.txt": "Арбитражный процессуальный кодекс",
        "GPK.txt": "Гражданский процессуальный кодекс",
        "KoAP.txt": "Кодекс об административных правонарушениях",
    }

    found = {}
    for code_file, code_name in expected_codes.items():
        code_path = codes_dir / code_file
        if code_path.exists():
            size = code_path.stat().st_size
            print(f"✅ {code_name}: {code_file} ({size} байт)")
            found[code_file] = True
        else:
            print(f"❌ {code_name}: {code_file} не найден")
            found[code_file] = False

    return found


def download_codes() -> None:
    """Выводит инструкции по загрузке кодексов."""
    print("\n📥 Для загрузки текстов кодексов:")
    print("1. Перейдите на один из сайтов:")
    print("   - https://www.consultant.ru/")
    print("   - https://www.garant.ru/")
    print("   - https://pravo.gov.ru/")
    print("\n2. Скачайте тексты кодексов в формате .txt")
    print("3. Сохраните в папку data/codes/ со следующими именами:")
    print("   - GK.txt — Гражданский кодекс")
    print("   - APK.txt — Арбитражный процессуальный кодекс")
    print("   - GPK.txt — Гражданский процессуальный кодекс")
    print("   - KoAP.txt — КоАП")


def run_indexer() -> bool:
    """Запускает индексатор кодексов."""
    print("\n📊 Запуск индексации...")
    try:
        result = subprocess.run(
            [sys.executable, "src/rag/indexer.py", "--codes", "data/codes"],
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Индексация завершена успешно")
            return True
        else:
            print(f"❌ Ошибка индексации: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут индексации (более 5 минут)")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_query() -> None:
    """Запускает тестовый запрос."""
    print("\n🧪 Тестовый запрос...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "Статья 330 ГК РФ неустойка"],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        print(result.stdout)
        if "неустойк" in result.stdout.lower():
            print("✅ Тестовый запрос выполнен успешно")
        else:
            print("⚠️ Тестовый запрос выполнен, но результат может быть неполным")
    except subprocess.TimeoutExpired:
        print("⚠️ Таймаут тестового запроса")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def main() -> None:
    """Основная функция."""
    print("=" * 60)
    print("🔧 Настройка RAG для юридического агента")
    print("=" * 60)

    # Проверка Docker
    if not check_docker():
        print("\n⚠️ Установите Docker Desktop и перезапустите скрипт")
        return

    if not check_docker_running():
        print("\n⚠️ Запустите Docker Desktop и перезапустите скрипт")
        return

    # Проверка PostgreSQL
    if not check_postgres():
        print("\n🚀 Запуск PostgreSQL...")
        if not start_docker():
            print("\n⚠️ Не удалось запустить Docker Compose")
            return
        import time
        time.sleep(5)  # Ждем запуска БД

    # Проверка кодексов
    found_codes = check_codes()
    if not any(found_codes.values()):
        print("\n⚠️ Тексты кодексов не найдены")
        download_codes()
        return

    # Индексация
    if not run_indexer():
        print("\n⚠️ Индексация не выполнена")
        return

    # Тестовый запрос
    test_query()

    print("\n" + "=" * 60)
    print("✅ Настройка завершена успешно!")
    print("=" * 60)
    print("\n📚 Дополнительные команды:")
    print("  - Запуск: python -m src.main \"ваш запрос\"")
    print("  - Тесты: pytest src/tests/test_e2e.py -v")
    print("  - Логи: Get-Content logs\\app.log -Wait")


if __name__ == "__main__":
    # UTF-8 для Windows
    if sys.platform == "win32":
        try:
            os.system("chcp 65001 >nul 2>&1")
        except:
            pass

    from dotenv import load_dotenv
    load_dotenv(override=True)

    main()
