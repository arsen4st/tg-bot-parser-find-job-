"""Глобальный обработчик ошибок бота."""

from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.types import Update

logger = logging.getLogger(__name__)


def setup_error_handler(dp: Dispatcher) -> None:
    """Регистрирует глобальный обработчик исключений."""

    @dp.error()
    async def error_handler(update: Update, exception: Exception) -> None:
        logger.exception("Ошибка при обработке update: %s", exception)
        if update.message:
            await update.message.answer(
                "❌ Произошла ошибка. Попробуй ещё раз или напиши /start."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "❌ Ошибка. Попробуй позже.", show_alert=True
            )
