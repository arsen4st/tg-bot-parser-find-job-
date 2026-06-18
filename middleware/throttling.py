"""Middleware для rate limiting команд."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничивает частоту команд от одного пользователя."""

    def __init__(self, rate_limit: float = 0.8) -> None:
        self.rate_limit = rate_limit
        self._last_call: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            now = time.time()
            last = self._last_call.get(user_id, 0)
            if now - last < self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("⏳ Слишком быстро. Подожди немного.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ Слишком быстро.", show_alert=True)
                return None
            self._last_call[user_id] = now

        return await handler(event, data)
