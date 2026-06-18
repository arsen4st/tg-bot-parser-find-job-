"""Telethon-клиент для мониторинга Telegram-каналов в реальном времени."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable

from telethon import TelegramClient, events
from telethon.errors import ChannelInvalidError, ChannelPrivateError, FloodWaitError
from telethon.tl.types import Channel

import config
from database import get_user_settings, list_channels, save_vacancy
from filters import RequirementFilter, extract_salary, is_actual, is_likely_vacancy

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
        self._cache_ttl = 30.0
        self._channels_cache: set[str] | None = None
        self._channels_ts: float = 0.0
        self._channels_ttl = 60.0

    async def start(self) -> None:
        await self.client.start()
        logger.info("Telethon клиент запущен")
        await self._backfill()
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
        now = time.time()
        if self._channels_cache is not None and now - self._channels_ts < self._channels_ttl:
            return self._channels_cache
        rows = await list_channels()
        self._channels_cache = {row["username"].lower() for row in rows}
        self._channels_ts = now
        return self._channels_cache

    async def _user_settings(self) -> dict:
        now = time.time()
        cached = self._settings_cache.get("user")
        if cached and now - cached["ts"] < self._cache_ttl:
            return cached["settings"]
        settings = await get_user_settings(config.ADMIN_ID)
        self._settings_cache["user"] = {"settings": settings, "ts": now}
        return settings

    async def _backfill(self, limit: int = 20) -> None:
        channels = await list_channels()
        if not channels:
            logger.info("Нет каналов для backfill")
            return
        tasks = [self._read_history(ch["username"], limit) for ch in channels]
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

        settings = await self._user_settings()
        requirements = settings.get("requirements", "")
        min_salary = settings.get("min_salary", 0)
        salary_filter_enabled = settings.get("salary_filter_enabled", False)
        max_age_days = settings.get("max_age_days", 0)

        filt = RequirementFilter.parse(requirements)
        matched, score = filt.match(text)

        # Проверка актуальности
        msg_date = message.date
        if msg_date and msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        if not is_actual(msg_date, max_age_days):
            matched = False
            score -= 2.0

        # Проверка минимальной зарплаты
        salary = extract_salary(text)
        if salary_filter_enabled and min_salary > 0:
            if salary is None or salary < min_salary:
                matched = False
                score -= 1.0
        if salary:
            score += min(salary / 100000, 1.0)  # небольшой бонус за высокую зп

        saved = await save_vacancy(
            channel_username=username,
            message_id=message.id,
            text=text,
            score=score,
            matched=matched,
            salary=salary,
        )
        if not saved:
            return

        if not matched or settings.get("paused", False):
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
            "salary": salary,
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
        return f"https://t.me/c/{entity.id}/{message_id}"

    @staticmethod
    def _trim(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."
