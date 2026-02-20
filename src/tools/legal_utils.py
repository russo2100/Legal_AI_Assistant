"""
Вспомогательные утилиты для юридической логики.

Содержит функции для нормализации, форматирования и обработки юридических текстов.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LegalReference:
    """Ссылка на нормативный акт."""

    code: str  # ГК, АПК, ГПК, КоАП
    article: str  # Номер статьи
    part: Optional[str] = None  # Часть/пункт
    paragraph: Optional[str] = None  # Подпункт


def normalize_query(query: str) -> str:
    """
    Нормализует юридический запрос.

    Args:
        query: Исходный запрос.

    Returns:
        Нормализованный запрос.
    """
    # Приведение к нижнему регистру
    query = query.lower()

    # Удаление лишних пробелов
    query = re.sub(r"\s+", " ", query).strip()

    # Замена распространённых сокращений
    replacements = {
        "гр. кодекс": "гк",
        "гражданский кодекс": "гк",
        "арбитражный процессуальный кодекс": "апк",
        "гражданский процессуальный кодекс": "гпк",
        "кодекс об административных правонарушениях": "коап",
        "ст.": "статья",
        "ст ": "статья ",
        "п.": "пункт",
        "ч.": "часть",
    }

    for old, new in replacements.items():
        query = query.replace(old, new)

    return query


def parse_legal_reference(text: str) -> Optional[LegalReference]:
    """
    Парсит юридическую ссылку из текста.

    Args:
        text: Текст со ссылкой.

    Returns:
        LegalReference или None если не найдено.
    """
    # Паттерн: ГК ст. 330, АПК статья 123 и т.д.
    pattern = r"\b(ГК|АПК|ГПК|КоАП|УК|УПК)\s*(?:ст\.?\s*|статья\s+)(\d+)(?:\s*(?:ч\.?\s*|часть\s+)(\d+))?(?:\s*(?:п\.?\s*|пункт\s+)(\d+))?"

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return LegalReference(
            code=match.group(1).upper(),
            article=match.group(2),
            part=match.group(3),
            paragraph=match.group(4),
        )

    return None


def format_case_number(case_number: str) -> str:
    """
    Форматирует номер арбитражного дела.

    Args:
        case_number: Исходный номер дела.

    Returns:
        Форматированный номер (А40-123456/2024).
    """
    # Очистка от лишних символов
    case_number = re.sub(r"[^\dА-Яа-я/]", "", case_number.upper())

    # Приведение к стандартному формату
    pattern = r"(А\d+)(\d+)/(\d{4})"
    match = re.match(pattern, case_number)

    if match:
        return f"{match.group(1)}-{match.group(2)}/{match.group(3)}"

    return case_number


def extract_monetary_amount(text: str) -> Optional[dict]:
    """
    Извлекает денежные суммы из текста.

    Args:
        text: Текст с суммами.

    Returns:
        Dict с amount и currency или None.
    """
    # Паттерны для сумм: 1000 руб., 1 млн. рублей, $5000
    patterns = [
        r"(\d+(?:\s*\d{3})*(?:\.\d+)?)\s*(руб\.?|рублей|₽)",
        r"(\d+(?:\.\d+)?)\s*(млн\.?|миллионов?|млрд\.?|миллиардов?)\s*(руб\.?)?",
        r"(\$|€|£)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()

            if "$" in pattern or "€" in pattern or "£" in pattern:
                return {"amount": float(groups[1].replace(",", "")), "currency": groups[0]}
            else:
                amount = float(groups[0].replace(" ", "").replace(",", "."))
                multiplier = 1

                if len(groups) > 2 and groups[2]:
                    mult_text = groups[2].lower()
                    if "млн" in mult_text or "миллион" in mult_text:
                        multiplier = 1_000_000
                    elif "млрд" in mult_text or "миллиард" in mult_text:
                        multiplier = 1_000_000_000

                currency = groups[-1] if groups[-1] else "RUB"
                if currency in ("руб", "руб.", "рублей"):
                    currency = "RUB"

                return {"amount": amount * multiplier, "currency": currency}

    return None


def calculate_penalty(
    principal: float,
    rate: float,
    days: int,
    penalty_type: str = "simple",
) -> float:
    """
    Рассчитывает неустойку.

    Args:
        principal: Основная сумма долга.
        rate: Процентная ставка (годовых).
        days: Количество дней просрочки.
        penalty_type: Тип расчёта (simple, compound, key_rate).

    Returns:
        Сумма неустойки.
    """
    if penalty_type == "simple":
        # Простая неустойка
        return principal * (rate / 100) * days / 365

    elif penalty_type == "compound":
        # Сложная неустойка (с капитализацией)
        return principal * ((1 + rate / 100 / 365) ** days - 1)

    elif penalty_type == "key_rate":
        # По ключевой ставке ЦБ (ст. 395 ГК РФ)
        return principal * (rate / 100) * days / 365

    else:
        raise ValueError(f"Неизвестный тип неустойки: {penalty_type}")


def get_limitation_period(claim_type: str) -> int:
    """
    Возвращает срок исковой давности.

    Args:
        claim_type: Тип требования.

    Returns:
        Срок в годах.
    """
    # По умолчанию - общий срок (ст. 196 ГК РФ)
    default_period = 3

    periods = {
        "договор": 3,
        "неустойка": 3,
        "убытки": 3,
        "качество": 2,  # Для требований о качестве (ст. 725 ГК)
        "аренда": 1,  # Краткосрочная аренда
        "перевозка": 1,  # Требования из перевозки
    }

    return periods.get(claim_type.lower(), default_period)


def format_date_russian(date: datetime) -> str:
    """
    Форматирует дату по-русски.

    Args:
        date: Дата для форматирования.

    Returns:
        Строка в формате "20 февраля 2026 г.".
    """
    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }

    day = date.day
    month = months[date.month]
    year = date.year

    return f"{day} {month} {year} г."


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Сanitizes входные данные для защиты от prompt-injection.

    Args:
        text: Исходный текст.
        max_length: Максимальная длина.

    Returns:
        Очищенный текст.
    """
    # Ограничение длины
    text = text[:max_length]

    # Удаление потенциально опасных конструкций
    dangerous_patterns = [
        r"ignore\s+previous\s+instructions",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"developer\s+mode",
        r"dan\s+mode",
    ]

    for pattern in dangerous_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()
