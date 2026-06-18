"""Работа с вакансиями."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

import config
from database import (
    get_saved_count,
    get_vacancy_by_url_hash,
    is_vacancy_saved,
    remove_saved,
    save_vacancy_to_favorites,
)
from keyboards.main import vacancy_button
from utils.formatter import format_vacancy

logger = logging.getLogger(__name__)
router = Router()


def _url_hash(channel_username: str, message_id: int) -> str:
    raw = f"{channel_username.lower().strip()}:{message_id}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _ts_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


async def send_vacancy(vacancy: dict) -> None:
    """Отправляет вакансию админу. Вызывается из parser.py."""
    from bot import bot

    try:
        channel = vacancy["channel_username"]
        message_id = vacancy["message_id"]
        url = vacancy["link"]
        url_hash = vacancy.get("url_hash") or _url_hash(channel, message_id)
        date = _ts_to_datetime(vacancy.get("created_at"))
        text = vacancy.get("full_text") or vacancy.get("text") or ""

        is_saved, saved_id = await is_vacancy_saved(config.ADMIN_ID, url_hash)
        formatted = format_vacancy(text, channel, url, date)

        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=formatted,
            reply_markup=vacancy_button(url, url_hash, is_saved, saved_id),
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML,
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
    await _send_latest(message, limit)


async def _send_latest(message: types.Message, limit: int) -> None:
    from database import get_latest_vacancies

    limit = max(1, min(limit, 25))
    vacancies = await get_latest_vacancies(limit=limit, only_matched=False)

    if not vacancies:
        await message.answer("📭 Пока нет сохранённых вакансий.")
        return

    await message.answer(f"📋 Последние {len(vacancies)} вакансий:")

    for v in vacancies:
        channel = v["channel_username"]
        message_id = v["message_id"]
        url = f"https://t.me/{channel}/{message_id}"
        url_hash = v.get("url_hash") or _url_hash(channel, message_id)
        date = _ts_to_datetime(v.get("created_at"))
        text = v.get("text") or ""
        is_saved, saved_id = await is_vacancy_saved(message.from_user.id, url_hash)
        formatted = format_vacancy(text, channel, url, date)
        try:
            await message.answer(
                text=formatted,
                reply_markup=vacancy_button(url, url_hash, is_saved, saved_id),
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:
            logger.exception("Ошибка отправки /latest: %s", exc)
        await asyncio.sleep(0.05)


@router.callback_query(lambda c: c.data == "latest_vacancies")
async def cb_latest_vacancies(callback: types.CallbackQuery) -> None:
    await _send_latest(callback.message, limit=10)
    await callback.answer()


# ---------------------------------------------------------------------------
# Сохранение / удаление из избранного
# ---------------------------------------------------------------------------
CB_SAVE_PREFIX = "save:"
CB_UNSAVE_PREFIX = "unsave:"


@router.callback_query(F.data.startswith(CB_SAVE_PREFIX))
async def cb_save_vacancy(callback: types.CallbackQuery) -> None:
    url_hash = callback.data[len(CB_SAVE_PREFIX) :]
    vacancy = await get_vacancy_by_url_hash(url_hash)
    if not vacancy:
        await callback.answer("❌ Вакансия не найдена.", show_alert=True)
        return

    link = f"https://t.me/{vacancy['channel_username']}/{vacancy['message_id']}"
    saved_id = await save_vacancy_to_favorites(
        user_id=callback.from_user.id,
        vacancy_id=vacancy["id"],
        channel=vacancy["channel_username"],
        text=vacancy["text"],
        url=link,
    )
    if saved_id is None:
        await callback.answer("❌ Уже сохранено.", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(
            reply_markup=vacancy_button(link, url_hash, True, saved_id)
        )
    except Exception as exc:
        logger.exception("Ошибка обновления кнопки: %s", exc)

    await callback.answer("Сохранено ✅")
    saved_count = await get_saved_count(callback.from_user.id)
    logger.info(
        "Пользователь %s сохранил вакансию. Всего сохранено: %s",
        callback.from_user.id,
        saved_count,
    )


@router.callback_query(F.data.startswith(CB_UNSAVE_PREFIX))
async def cb_unsave_vacancy(callback: types.CallbackQuery) -> None:
    parts = callback.data[len(CB_UNSAVE_PREFIX) :].split(":")
    try:
        saved_id = int(parts[0])
        url_hash = parts[1] if len(parts) > 1 else ""
    except (ValueError, IndexError):
        await callback.answer("❌ Некорректные данные.", show_alert=True)
        return

    ok = await remove_saved(saved_id)
    if not ok:
        await callback.answer("❌ Вакансия не найдена.", show_alert=True)
        return

    link = ""
    if callback.message.reply_markup and callback.message.reply_markup.inline_keyboard:
        link = callback.message.reply_markup.inline_keyboard[0][0].url or ""
    if not link and url_hash:
        vacancy = await get_vacancy_by_url_hash(url_hash)
        if vacancy:
            link = f"https://t.me/{vacancy['channel_username']}/{vacancy['message_id']}"

    try:
        await callback.message.edit_reply_markup(
            reply_markup=vacancy_button(link, url_hash, False, None)
        )
    except Exception as exc:
        logger.exception("Ошибка обновления кнопки: %s", exc)

    await callback.answer("Удалено из избранного")
