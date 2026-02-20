"""
Модуль загрузки и рендеринга Jinja2-шаблонов.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Загрузчик промпт-шаблонов.

    Attributes:
        env: Jinja2 environment.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Инициализирует загрузчик.

        Args:
            templates_dir: Путь к директории с шаблонами.
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "prompts"

        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.info(f"PromptLoader инициализирован: {self.templates_dir}")

    def get_template(self, name: str) -> Template:
        """
        Загружает шаблон по имени.

        Args:
            name: Имя шаблона (без расширения).

        Returns:
            Jinja2 Template.
        """
        return self.env.get_template(f"{name}.j2")

    def render(self, name: str, **context: Any) -> str:
        """
        Рендерит шаблон с контекстом.

        Args:
            name: Имя шаблона.
            **context: Переменные для шаблона.

        Returns:
            Отрендеренная строка.
        """
        template = self.get_template(name)
        return template.render(**context)


# Глобальный экземпляр
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Возвращает глобальный экземпляр загрузчика."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader


def render_prompt(name: str, **context: Any) -> str:
    """Удобная функция для рендеринга промпта."""
    return get_prompt_loader().render(name, **context)
