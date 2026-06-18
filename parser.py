"""Telethon-клиент для мониторинга Telegram-каналов в реальном времени."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from telethon import TelegramClient, events
from telethon.errors import ChannelInvalidError, ChannelPrivateError, FloodWaitError
from telethon.tl.types import Channel

import config
from database import (
    list_channels,
    save_vacancy,
)
from filters import RequirementFilter, is_likely_vacancy

logger = logging.getLogger(__name__)

VacancyCallback = Callable[[dict], Awaitable[None]]


class VacancyParser:
    def __init__(self, callback: VacancyCallback) -> None:
        self.client = TelegramClient(
            config.SESSION_NAME,
            config.API_ID,
            config.API_HASH,
        )
        self.callback = callback
        self._handler = None
        self._settings_cache: dict[str, tuple] = {}
        self._cache_ttl = 30.0  # секунд
        self._channels_cache: set[str] | None = None
        self._channels_ts: float = 0.0
        self._channels_ttl = 60.0  # секунд

    async def start(self) -> None:
        await self.client.start()
        logger.info("Telethon клиент запущен")

        # Подгружаем последние посты из уже добавленных каналов
        await self._backfill()

        # Вешаем обработчик новых сообщений
        self._handler = self.client.add_event_handler(
            self._on_new_message,
            events.NewMessage,
        )

    async def run_until_disconnected(self) -> None:
        await self.client.run_until_disconnected()

    async def stop(self) -> None:
        if self._handler:
            self.client.remove_event_handler(self._handler)
        await self.client.disconnect()

    async def _tracked_channels(self) -> set[str]:
        """Возвращает множество отслеживаемых каналов с кэшированием."""
        now = time.time()
        if self._channels_cache is not None and now - self._channels_ts < self._channels_ttl:
            return self._channels_cache

        rows = await list_channels()
        self._channels_cache = {row["username"].lower() for row in rows}
        self._channels_ts = now
        return self._channels_cache

    async def _user_settings(self) -> tuple[str, bool]:
        """Возвращает (requirements, paused) с кэшированием."""
        now = time.time()
        cached = self._settings_cache.get("user")
        if cached and now - cached["ts"] < self._cache_ttl:
            return cached["req"], cached["paused"]

        req = await get_requirements(config.ADMIN_ID)
        paused = await is_paused(config.ADMIN_ID)
        self._settings_cache["user"] = {
            "req": req,
            "paused": paused,
            "ts": now,
        }
        return req, paused

    async def _backfill(self, limit: int = 20) -> None:
        """При старте читает последние N сообщений из каждого канала."""
        channels = await list_channels()
        if not channels:
            logger.info("Нет каналов для backfill")
            return

        tasks = [
            self._read_history(ch["username"], limit)
            for ch in channels
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _read_history(self, username: str, limit: int) -> None:
        try:
            entity = await self.client.get_entity(username)
        except (ChannelInvalidError, ChannelPrivateError, ValueError) as exc:
            logger.warning("Не удалось получить канал %s: %s", username, exc)
            return

        try:
            async for message in self.client.iter_messages(entity, limit=limit):
                if not message or not message.text:
                    continue
                await self._process_message(message, entity)
        except FloodWaitError as exc:
            logger.warning("FloodWait на канале %s: %s сек", username, exc.seconds)
        except Exception as exc:
            logger.exception("Ошибка backfill для %s: %s", username, exc)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        message = event.message
        if not message or not message.text:
            return

        chat = await event.get_chat()
        await self._process_message(message, chat)

    async def _process_message(self, message, entity) -> None:
        # Работаем только с публичными каналами
        if not isinstance(entity, Channel):
            return

        username = getattr(entity, "username", None)
        if not username:
            return

        username = username.lower()
        if username not in await self._tracked_channels():
            return

        text = message.text or ""
        if not is_likely_vacancy(text):
            return

        requirements, paused = await self._user_settings()
        filt = RequirementFilter.parse(requirements)
        matched, score = filt.match(text)

        # Сохраняем вакансию независимо от matched — полезно для /latest
        saved = await save_vacancy(
            channel_username=username,
            message_id=message.id,
            text=text,
            score=score,
            matched=matched,
        )

        if not saved:
            # Уже видели
            return

        if not matched:
            return

        if paused:
            return

        link = self._message_link(entity, message.id)
        preview_text = self._trim(text, config.MAX_MESSAGE_LENGTH)

        vacancy = {
            "channel_username": username,
            "message_id": message.id,
            "text": preview_text,
            "full_text": text,
            "score": score,
            "link": link,
        }

        try:
            await self.callback(vacancy)
        except Exception as exc:
            logger.exception("Ошибка отправки вакансии в бот: %s", exc)

    @staticmethod
    def _message_link(entity: Channel, message_id: int) -> str:
        username = getattr(entity, "username", "")
        if username:
            return f"https://t.me/{username}/{message_id}"
        # Для приватных каналов пытаемся сделать private-ссылку
        return f"https://t.me/c/{entity.id}/{message_id}"

    @staticmethod
    def _trim(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."
