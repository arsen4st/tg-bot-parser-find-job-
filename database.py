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
                    salary INTEGER DEFAULT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(channel_username, message_id)
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    requirements TEXT DEFAULT '',
                    paused INTEGER DEFAULT 0,
                    min_salary INTEGER DEFAULT 0,
                    salary_filter_enabled INTEGER DEFAULT 0,
                    max_age_days INTEGER DEFAULT 0
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

    await _migrate_db()


async def _migrate_db() -> None:
    """Добавляет недостающие колонки в существующие таблицы."""
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            for column, col_type in [
                ("min_salary", "INTEGER DEFAULT 0"),
                ("salary_filter_enabled", "INTEGER DEFAULT 0"),
                ("max_age_days", "INTEGER DEFAULT 0"),
                ("salary", "INTEGER DEFAULT NULL"),
            ]:
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
                    await db.commit()
                except aiosqlite.OperationalError:
                    pass  # колонка уже есть


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
    channel_username: str,
    message_id: int,
    text: str,
    score: float,
    matched: bool,
    salary: int | None = None,
) -> bool:
    channel_username = channel_username.lower().strip()
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO vacancies
                        (channel_username, message_id, text, score, matched, salary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (channel_username, message_id, text, score, int(matched), salary, _now()),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def get_latest_vacancies(limit: int = 10, only_matched: bool = False) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT channel_username, message_id, text, score, matched, salary, created_at
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


async def set_min_salary(user_id: int, amount: int) -> None:
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, min_salary)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET min_salary = excluded.min_salary
                """,
                (user_id, amount),
            )
            await db.commit()


async def get_min_salary(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT min_salary FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def set_salary_filter(user_id: int, enabled: bool) -> None:
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, salary_filter_enabled)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET salary_filter_enabled = excluded.salary_filter_enabled
                """,
                (user_id, int(enabled)),
            )
            await db.commit()


async def is_salary_filter_enabled(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT salary_filter_enabled FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False


async def set_max_age_days(user_id: int, days: int) -> None:
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, max_age_days)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET max_age_days = excluded.max_age_days
                """,
                (user_id, days),
            )
            await db.commit()


async def get_max_age_days(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT max_age_days FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_user_settings(user_id: int) -> dict:
    """Возвращает все настройки пользователя одним запросом."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT requirements, paused, min_salary, salary_filter_enabled, max_age_days
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {
                    "requirements": "",
                    "paused": False,
                    "min_salary": 0,
                    "salary_filter_enabled": False,
                    "max_age_days": 0,
                }
            return {
                "requirements": row["requirements"],
                "paused": bool(row["paused"]),
                "min_salary": row["min_salary"],
                "salary_filter_enabled": bool(row["salary_filter_enabled"]),
                "max_age_days": row["max_age_days"],
            }
