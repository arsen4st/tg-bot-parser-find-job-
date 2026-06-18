"""Работа с вакансиями."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

import config
from database import get_latest_vacancies
from keyboards.main import vacancy_button
from utils.helpers import escape_html, trim_text

logger = logging.getLogger(__name__)
router = Router()


def _format_vacancy(v: dict) -> str:
    channel = v["channel_username"]
    score = v.get("score", 0.0)
    ts = v.get("created_at")
    when = ""
    if ts:
        when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d.%m %H:%M")

    text = v.get("text", "")
    preview = escape_html(trim_text(text, config.MAX_MESSAGE_LENGTH))

    return (
        f"<b>💼 Вакансия</b>\n"
        f"<b>Канал:</b> @{escape_html(channel)}\n"
        f"<b>Совпадение:</b> {score:.1f}/10\n"
        f"<b>Время:</b> {when}\n\n"
        f"{preview}"
    )


async def send_vacancy(vacancy: dict) -> None:
    """Отправляет вакансию админу. Вызывается из parser.py."""
    from bot import bot

    try:
        link = vacancy["link"]
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=_format_vacancy(vacancy),
            reply_markup=vacancy_button(link),
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.exception("Не удалось отправить вакансию: %s", exc)


@router.message(Command("latest"))
async def cmd_latest(message: types.Message) -> None:
    args = message.text.split()
    try:
        limit = int(args[1]) if len(args) > 1 else config.DEFAULT_LATEST_LIMIT
    except ValueError:
        limit = config.DEFAULT_LATEST_LIMIT

    limit = max(1, min(limit, 25))
    vacancies = await get_latest_vacancies(limit=limit, only_matched=False)

    if not vacancies:
        await message.answer("📭 Пока нет сохранённых вакансий.")
        return

    await message.answer(f"📋 Последние {len(vacancies)} вакансий:")

    for v in vacancies:
        link = f"https://t.me/{v['channel_username']}/{v['message_id']}"
        try:
            await message.answer(
                text=_format_vacancy(v),
                reply_markup=vacancy_button(link),
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.exception("Ошибка отправки /latest: %s", exc)
        await asyncio.sleep(0.05)


@router.callback_query(lambda c: c.data == "latest_vacancies")
async def cb_latest_vacancies(callback: types.CallbackQuery) -> None:
    # Имитируем вызов команды /latest
    fake_message = callback.message
    fake_message.text = "/latest 10"
    await cmd_latest(fake_message)
    await callback.answer()
