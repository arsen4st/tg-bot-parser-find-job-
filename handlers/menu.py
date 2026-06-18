"""Главное меню и навигация."""

from __future__ import annotations

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

import config
from database import (
    get_max_age_days,
    get_min_salary,
    get_requirements,
    is_paused,
    is_salary_filter_enabled,
    list_channels,
    set_paused,
)
from keyboards.main import back_to_menu, main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        "👋 Привет! Я бот-парсер вакансий из Telegram-каналов.\n\n"
        "Что я умею:\n"
        "• Слежу за каналами в реальном времени\n"
        "• Фильтрую по твоим требованиям (+python -senior)\n"
        "• Присылаю вакансию с кнопкой на конкретный пост\n\n"
        "Выбери действие:",
        reply_markup=main_menu(),
    )


@router.callback_query(lambda c: c.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "👋 Главное меню. Выбери действие:",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "list_channels")
async def cb_list_channels(callback: types.CallbackQuery) -> None:
    channels = await list_channels()
    if not channels:
        text = "📭 Пока нет отслеживаемых каналов."
    else:
        lines = ["📡 Отслеживаемые каналы:"]
        for ch in channels:
            title = ch.get("title") or ""
            line = f"• @{ch['username']}"
            if title:
                line += f" — {title}"
            lines.append(line)
        text = "\n".join(lines)
    await callback.message.answer(text, reply_markup=back_to_menu())
    await callback.answer()


async def _build_status_text(user_id: int) -> str:
    channels = await list_channels()
    paused = await is_paused(user_id)
    req = await get_requirements(user_id) or "не заданы"
    min_salary = await get_min_salary(user_id)
    salary_enabled = await is_salary_filter_enabled(user_id)
    max_age = await get_max_age_days(user_id)

    return (
        f"📊 Статус:\n"
        f"Каналов: {len(channels)}\n"
        f"Рассылка: {'на паузе' if paused else 'активна'}\n"
        f"Требования: {req}\n"
        f"Мин. зарплата: {min_salary if salary_enabled else 'выкл'}\n"
        f"Макс. возраст: {max_age if max_age > 0 else 'не задан'}"
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    text = await _build_status_text(message.from_user.id)
    await message.answer(text, reply_markup=back_to_menu())


@router.callback_query(lambda c: c.data == "status")
async def cb_status(callback: types.CallbackQuery) -> None:
    text = await _build_status_text(callback.from_user.id)
    await callback.message.answer(text, reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "toggle_pause")
async def cb_toggle_pause(callback: types.CallbackQuery) -> None:
    user_id = callback.from_user.id
    paused = await is_paused(user_id)
    await set_paused(user_id, not paused)
    status = "на паузе ⏸" if not paused else "активна ▶️"
    await callback.message.answer(
        f"Рассылка {status}.",
        reply_markup=back_to_menu(),
    )
    await callback.answer()
