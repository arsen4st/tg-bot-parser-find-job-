"""Вспомогательные функции."""

from __future__ import annotations

import html

import config


def escape_html(text: str | None) -> str:
    """Безопасно экранирует HTML."""
    if text is None:
        return ""
    return html.escape(str(text))


def trim_text(text: str, max_len: int = config.MAX_MESSAGE_LENGTH) -> str:
    """Обрезает текст до max_len с добавлением '...'."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def parse_channel_username(text: str) -> str:
    """Извлекает @username из ссылки, @username или plain username."""
    text = text.strip()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    for prefix in ("t.me/", "telegram.me/"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("/")[0]
    if text.startswith("@"):
        text = text[1:]
    return text.lower().strip()


def format_number(n: int | float) -> str:
    """Форматирует число для человека."""
    return f"{n:.1f}" if isinstance(n, float) else str(n)
