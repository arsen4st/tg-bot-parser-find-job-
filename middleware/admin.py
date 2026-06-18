"""Middleware для проверки прав администратора."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

import config


class AdminMiddleware(BaseMiddleware):
    """Пропускает только сообщения от администратора."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            if event.from_user.id != config.ADMIN_ID:
                await event.answer("❌ Только админ может использовать этого бота.")
                return None
        return await handler(event, data)
