"""Админ-команды: авторизация, пауза, статус."""

from __future__ import annotations

import io
import logging

import qrcode
from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from telethon import TelegramClient

import config
from database import get_requirements, is_paused, list_channels, set_paused
from keyboards.main import back_to_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("login"))
async def cmd_login(message: types.Message) -> None:
    await message.answer("⏳ Генерирую QR-код для авторизации...")

    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    await client.connect()

    try:
        if await client.is_user_authorized():
            await message.answer(
                "✅ Уже авторизовано!\n"
                "Закрой бота и запусти <code>main.py</code> — парсер заработает.",
                parse_mode=ParseMode.HTML,
            )
            return

        qr_login = await client.qr_login()

        img = qrcode.make(qr_login.url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        from bot import bot

        await bot.send_photo(
            chat_id=config.ADMIN_ID,
            photo=types.BufferedInputFile(buf.getvalue(), filename="qr_login.png"),
            caption=(
                "📲 Отсканируй этот QR-код в Telegram:\n"
                "<b>Настройки → Устройства → Подключить устройство → Сканировать QR</b>\n\n"
                "После сканирования я напишу, что авторизация прошла."
            ),
            parse_mode=ParseMode.HTML,
        )

        await qr_login.wait()
        await message.answer(
            "✅ Авторизация успешна!\n"
            "Теперь перезапусти <code>start.bat</code> — парсер и бот заработают вместе.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Ошибка QR-авторизации")
        await message.answer(f"❌ Ошибка авторизации: {exc}")
    finally:
        await client.disconnect()


@router.message(Command("pause"))
async def cmd_pause(message: types.Message) -> None:
    await set_paused(message.from_user.id, True)
    await message.answer("⏸ Рассылка приостановлена.", reply_markup=back_to_menu())


@router.message(Command("resume"))
async def cmd_resume(message: types.Message) -> None:
    await set_paused(message.from_user.id, False)
    await message.answer("▶️ Рассылка возобновлена.", reply_markup=back_to_menu())


@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    channels = await list_channels()
    paused = await is_paused(message.from_user.id)
    req = await get_requirements(message.from_user.id) or "не заданы"
    await message.answer(
        f"📊 Статус:\n"
        f"Каналов: {len(channels)}\n"
        f"Рассылка: {'на паузе' if paused else 'активна'}\n"
        f"Требования: {req}",
        reply_markup=back_to_menu(),
    )
