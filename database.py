"""Асинхронная работа с SQLite."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import aiosqlite

from config import DB_PATH

_lock = asyncio.Lock()


def _now() -> int:
    return int(time.time())


async def init_db() -> None:
    """Создаёт таблицы и индексы, если их нет."""
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    title TEXT DEFAULT '',
                    added_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS vacancies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_username TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    score REAL DEFAULT 0.0,
                    matched INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    UNIQUE(channel_username, message_id)
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    requirements TEXT DEFAULT '',
                    paused INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_vacancies_created
                    ON vacancies(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_vacancies_channel
                    ON vacancies(channel_username);
                CREATE INDEX IF NOT EXISTS idx_vacancies_matched
                    ON vacancies(matched, score DESC);
                """
            )
            await db.commit()


async def add_channel(username: str, title: str = "") -> bool:
    username = username.lower().strip().replace("https://t.me/", "").replace("@", "")
    if not username:
        return False
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO channels (username, title, added_at) VALUES (?, ?, ?)",
                    (username, title, _now()),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def remove_channel(username: str) -> bool:
    username = username.lower().strip().replace("https://t.me/", "").replace("@", "")
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("DELETE FROM channels WHERE username = ?", (username,))
            await db.commit()
            return cursor.rowcount > 0


async def list_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT username, title, added_at FROM channels ORDER BY added_at"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def channel_exists(username: str) -> bool:
    username = username.lower().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM channels WHERE username = ? LIMIT 1", (username,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def save_vacancy(
    channel_username: str, message_id: int, text: str, score: float, matched: bool
) -> bool:
    channel_username = channel_username.lower().strip()
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO vacancies
                        (channel_username, message_id, text, score, matched, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (channel_username, message_id, text, score, int(matched), _now()),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def get_latest_vacancies(limit: int = 10, only_matched: bool = False) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT channel_username, message_id, text, score, matched, created_at
            FROM vacancies
        """
        if only_matched:
            query += " WHERE matched = 1"
        query += " ORDER BY created_at DESC LIMIT ?"

        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def set_requirements(user_id: int, requirements: str) -> None:
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, requirements)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET requirements = excluded.requirements
                """,
                (user_id, requirements.strip().lower()),
            )
            await db.commit()


async def get_requirements(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT requirements FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_paused(user_id: int, paused: bool) -> None:
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, paused)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET paused = excluded.paused
                """,
                (user_id, int(paused)),
            )
            await db.commit()


async def is_paused(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT paused FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False
