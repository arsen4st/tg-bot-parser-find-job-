"""Основные клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """Главное инлайн-меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton(text="🔧 Задать фильтр", callback_data="set_filter")],
            [InlineKeyboardButton(text="📋 Мои каналы", callback_data="list_channels")],
            [InlineKeyboardButton(text="📋 Последние вакансии", callback_data="latest_vacancies")],
            [InlineKeyboardButton(text="📊 Статус", callback_data="status")],
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


def back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")],
        ]
    )


def channels_management(channels: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура управления каналами: каждый канал с кнопкой удаления."""
    buttons = []
    for ch in channels:
        username = ch["username"]
        buttons.append(
            [
                InlineKeyboardButton(text=f"@{username}", url=f"https://t.me/{username}"),
                InlineKeyboardButton(text="❌", callback_data=f"remove_channel:{username}"),
            ]
        )
    buttons.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
