"""
Скрипт проверки реквизитов документа.

Использование:
    python validate_requisites.py --type contract --file document.txt
"""

import argparse
import re
import sys
from pathlib import Path


class RequisitesValidator:
    """Валидатор реквизитов документов."""

    # Паттерны для проверки
    PATTERNS = {
        'inn_yur': r'\d{10}',  # ИНН юрлица
        'inn_ip': r'\d{12}',   # ИНН ИП
        'kpp': r'\d{9}',       # КПП
        'ogrn': r'\d{13}',     # ОГРН
        'ogrnip': r'\d{15}',   # ОГРНИП
        'bik': r'\d{9}',       # БИК
        'schet': r'\d{20}',    # Расчётный счёт
    }

    def __init__(self, doc_type: str):
        self.doc_type = doc_type
        self.errors = []
        self.warnings = []

    def validate_contract(self, text: str) -> bool:
        """Проверка реквизитов договора."""
        # Проверка ИНН
        if not re.search(self.PATTERNS['inn_yur'], text):
            self.errors.append("Не найден ИНН юрлица (10 цифр)")

        # Проверка КПП
        if not re.search(self.PATTERNS['kpp'], text):
            self.warnings.append("Не найден КПП (рекомендуется указать)")

        # Проверка ОГРН
        if not re.search(self.PATTERNS['ogrn'], text):
            self.warnings.append("Не найден ОГРН (рекомендуется указать)")

        # Проверка БИК
        if not re.search(self.PATTERNS['bik'], text):
            self.errors.append("Не найден БИК банка")

        # Проверка счёта
        if not re.search(self.PATTERNS['schet'], text):
            self.errors.append("Не найден расчётный счёт (20 цифр)")

        # Проверка даты
        if not re.search(r'«\d{1,2}»\s+\w+\s+\d{4}', text):
            self.warnings.append("Дата в договоре не найдена или в неверном формате")

        return len(self.errors) == 0

    def validate_claim(self, text: str) -> bool:
        """Проверка искового заявления."""
        # Проверка названия суда
        if not re.search(r'(Арбитражный\s+суд|суд\s+общей\s+юрисдикции)', text, re.IGNORECASE):
            self.errors.append("Не указано наименование суда")

        # Проверка сторон
        if not re.search(r'(Истец|Ответчик)', text):
            self.errors.append("Не указаны стороны (Истец/Ответчик)")

        # Проверка цены иска
        if not re.search(r'Цена\s+иска', text, re.IGNORECASE):
            self.warnings.append("Не указана цена иска (если подлежит оценке)")

        # Проверка госпошлины
        if not re.search(r'госпошлин', text, re.IGNORECASE):
            self.warnings.append("Не указано уплата госпошлины")

        # Проверка приложений
        if not re.search(r'(Приложен|Приложенн)', text, re.IGNORECASE):
            self.warnings.append("Не указан список приложений")

        return len(self.errors) == 0

    def validate(self, text: str) -> bool:
        """Основной метод валидации."""
        if self.doc_type == 'contract':
            return self.validate_contract(text)
        elif self.doc_type == 'claim':
            return self.validate_claim(text)
        else:
            self.warnings.append(f"Неизвестный тип документа: {self.doc_type}")
            return True

    def report(self) -> str:
        """Формирование отчёта."""
        lines = []

        if self.errors:
            lines.append("❌ ОШИБКИ:")
            for error in self.errors:
                lines.append(f"   - {error}")

        if self.warnings:
            lines.append("⚠️ ПРЕУПРЕЖДЕНИЯ:")
            for warning in self.warnings:
                lines.append(f"   - {warning}")

        if not self.errors and not self.warnings:
            lines.append("✅ Все реквизиты в порядке")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Проверка реквизитов документа')
    parser.add_argument('--type', required=True, choices=['contract', 'claim', 'pretenziya'],
                        help='Тип документа')
    parser.add_argument('--file', required=True, help='Путь к файлу документа')

    args = parser.parse_args()

    # Чтение файла
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ Файл не найден: {file_path}")
        sys.exit(1)

    text = file_path.read_text(encoding='utf-8')

    # Валидация
    validator = RequisitesValidator(args.type)
    is_valid = validator.validate(text)

    # Вывод отчёта
    print(f"\n📄 ПРОВЕРКА РЕКВИЗИТОВ: {file_path.name}")
    print("=" * 50)
    print(validator.report())
    print("=" * 50)

    if is_valid:
        print("✅ Документ прошёл проверку реквизитов")
        sys.exit(0)
    else:
        print("❌ Документ содержит ошибки в реквизитах")
        sys.exit(1)


if __name__ == '__main__':
    main()
