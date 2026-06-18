"""Обработка reply-меню внизу чата."""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from handlers.channels import cmd_add_channel
from handlers.filters import cmd_requirements
from handlers.vacancies import cmd_latest

router = Router()


@router.message(F.text == "➕ Добавить канал")
async def reply_add(message: types.Message, state: FSMContext) -> None:
    message.text = "/addchannel"
    await cmd_add_channel(message, state)


@router.message(F.text == "🔧 Фильтр")
async def reply_filter(message: types.Message) -> None:
    message.text = "/requirements"
    await cmd_requirements(message)


@router.message(F.text == "📋 Каналы")
async def reply_channels(message: types.Message) -> None:
    from handlers.channels import cmd_channels

    await cmd_channels(message)


@router.message(F.text == "📄 Вакансии")
async def reply_vacancies(message: types.Message) -> None:
    message.text = "/latest 10"
    await cmd_latest(message)


@router.message(F.text == "⏸ Пауза")
async def reply_pause(message: types.Message) -> None:
    from handlers.admin import cmd_pause

    await cmd_pause(message)


@router.message(F.text == "▶️ Старт")
async def reply_resume(message: types.Message) -> None:
    from handlers.admin import cmd_resume

    await cmd_resume(message)
