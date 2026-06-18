"""Основные клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """Главное инлайн-меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton(text="👤 Профили", callback_data="profiles")],
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


def profiles_list(profiles: list[dict]) -> InlineKeyboardMarkup:
    """Список профилей с активным и кнопкой создания нового."""
    buttons = []
    for p in profiles:
        prefix = "✅ " if p.get("is_active") else ""
        name = f"{prefix}{p['name']}"
        buttons.append(
            [InlineKeyboardButton(text=name, callback_data=f"profile_menu:{p['id']}")]
        )
    buttons.append([InlineKeyboardButton(text="➕ Новый профиль", callback_data="new_profile")])
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_menu(profile_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Под-меню профиля."""
    buttons = []
    if not is_active:
        buttons.append(
            [InlineKeyboardButton(text="✅ Активировать", callback_data=f"activate_profile:{profile_id}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"edit_profile:{profile_id}")]
    )
    buttons.append(
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_profile:{profile_id}")]
    )
    buttons.append([InlineKeyboardButton(text="◀️ К профилям", callback_data="profiles")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def profile_filters_menu(profile_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования фильтров профиля."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Включить слова", callback_data=f"edit_include:{profile_id}")],
            [InlineKeyboardButton(text="➖ Исключить слова", callback_data=f"edit_exclude:{profile_id}")],
            [InlineKeyboardButton(text="💰 Мин. зарплата", callback_data=f"edit_salary:{profile_id}")],
            [InlineKeyboardButton(text="📅 Макс. возраст", callback_data=f"edit_age:{profile_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"profile_menu:{profile_id}")],
        ]
    )


def confirm_delete_profile(profile_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления профиля."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_profile:{profile_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"profile_menu:{profile_id}"),
            ]
        ]
    )
