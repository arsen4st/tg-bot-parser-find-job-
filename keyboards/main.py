"""Основные клавиатуры бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu() -> InlineKeyboardMarkup:
    """Главное инлайн-меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton(text="🔧 Задать фильтр", callback_data="set_filter")],
            [InlineKeyboardButton(text="📋 Мои каналы", callback_data="list_channels")],
            [InlineKeyboardButton(text="📋 Последние вакансии", callback_data="latest_vacancies")],
            [InlineKeyboardButton(text="⏸ Пауза / ▶️ Старт", callback_data="toggle_pause")],
        ]
    )


def vacancy_button(link: str) -> InlineKeyboardMarkup:
    """Кнопка перехода к вакансии."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Перейти к вакансии", url=link)],
        ]
    )


def reply_main_menu() -> ReplyKeyboardMarkup:
    """Постоянное reply-меню внизу чата."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить канал"), KeyboardButton(text="🔧 Фильтр")],
            [KeyboardButton(text="📋 Каналы"), KeyboardButton(text="📄 Вакансии")],
            [KeyboardButton(text="⏸ Пауза"), KeyboardButton(text="▶️ Старт")],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")],
        ]
    )
