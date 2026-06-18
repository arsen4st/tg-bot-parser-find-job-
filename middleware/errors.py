"""Глобальный обработчик ошибок бота."""

from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.types import Update

logger = logging.getLogger(__name__)


def setup_error_handler(dp: Dispatcher) -> None:
    """Регистрирует глобальный обработчик исключений."""

    @dp.error()
    async def error_handler(event: Update, data: dict) -> None:
        exception = data.get("exception")
        logger.exception("Ошибка при обработке update: %s", exception)
        if event.message:
            await event.message.answer(
                "❌ Произошла ошибка. Попробуй ещё раз или напиши /start."
            )
        elif event.callback_query:
            await event.callback_query.answer(
                "❌ Ошибка. Попробуй позже.", show_alert=True
            )
