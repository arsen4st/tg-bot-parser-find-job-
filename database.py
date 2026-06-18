"""Асинхронная работа с SQLite."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from config import DB_PATH

_lock = asyncio.Lock()


def _now() -> int:
    return int(time.time())


def _dt_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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
                    paused INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    keywords_include TEXT DEFAULT '',
                    keywords_exclude TEXT DEFAULT '',
                    min_salary INTEGER DEFAULT 0,
                    salary_filter_on INTEGER DEFAULT 0,
                    max_age_days INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_vacancies_created
                    ON vacancies(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_vacancies_channel
                    ON vacancies(channel_username);
                CREATE INDEX IF NOT EXISTS idx_vacancies_matched
                    ON vacancies(matched, score DESC);
                CREATE INDEX IF NOT EXISTS idx_profiles_user
                    ON profiles(user_id);
                """
            )
            await db.commit()

    await _migrate_db()


async def _migrate_db() -> None:
    """Добавляет недостающие колонки в существующие таблицы."""
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            for table, column, col_type in [
                ("vacancies", "salary", "INTEGER DEFAULT NULL"),
                ("users", "paused", "INTEGER DEFAULT 0"),
            ]:
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    await db.commit()
                except aiosqlite.OperationalError:
                    pass


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Vacancies
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Users (paused state)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
async def create_profile(user_id: int, name: str) -> int:
    """Создаёт профиль, делает его активным, остальные деактивирует."""
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE profiles SET is_active = 0 WHERE user_id = ?",
                (user_id,),
            )
            cursor = await db.execute(
                """
                INSERT INTO profiles
                    (user_id, name, keywords_include, keywords_exclude, min_salary,
                     salary_filter_on, max_age_days, is_active, created_at)
                VALUES (?, ?, '', '', 0, 0, 0, 1, ?)
                """,
                (user_id, name, _dt_now()),
            )
            await db.commit()
            return cursor.lastrowid


async def list_profiles(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, name, keywords_include, keywords_exclude, min_salary,
                   salary_filter_on, max_age_days, is_active, created_at
            FROM profiles
            WHERE user_id = ?
            ORDER BY created_at
            """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_profile(profile_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, name, keywords_include, keywords_exclude, min_salary,
                   salary_filter_on, max_age_days, is_active, created_at
            FROM profiles
            WHERE id = ?
            """,
            (profile_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_active_profile(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, name, keywords_include, keywords_exclude, min_salary,
                   salary_filter_on, max_age_days, is_active, created_at
            FROM profiles
            WHERE user_id = ? AND is_active = 1
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_active_profile(user_id: int, profile_id: int) -> bool:
    profile = await get_profile(profile_id)
    if not profile or profile["user_id"] != user_id:
        return False
    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE profiles SET is_active = 0 WHERE user_id = ?",
                (user_id,),
            )
            await db.execute(
                "UPDATE profiles SET is_active = 1 WHERE id = ?",
                (profile_id,),
            )
            await db.commit()
    return True


async def update_profile(profile_id: int, **fields) -> bool:
    allowed = {
        "name",
        "keywords_include",
        "keywords_exclude",
        "min_salary",
        "salary_filter_on",
        "max_age_days",
    }
    to_update = {k: v for k, v in fields.items() if k in allowed}
    if not to_update:
        return False

    profile = await get_profile(profile_id)
    if not profile:
        return False

    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            set_clause = ", ".join(f"{k} = ?" for k in to_update)
            values = list(to_update.values()) + [profile_id]
            await db.execute(
                f"UPDATE profiles SET {set_clause} WHERE id = ?",
                values,
            )
            await db.commit()
    return True


async def delete_profile(profile_id: int) -> bool:
    profile = await get_profile(profile_id)
    if not profile:
        return False
    if profile.get("is_active"):
        return False

    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            await db.commit()
            return cursor.rowcount > 0


async def get_active_filters(user_id: int) -> dict:
    """Возвращает настройки активного профиля для парсера."""
    profile = await get_active_profile(user_id)
    if profile:
        return {
            "profile_id": profile["id"],
            "name": profile["name"],
            "requirements": _keywords_to_req(profile["keywords_include"], profile["keywords_exclude"]),
            "keywords_include": profile["keywords_include"],
            "keywords_exclude": profile["keywords_exclude"],
            "min_salary": profile["min_salary"] or 0,
            "salary_filter_enabled": bool(profile["salary_filter_on"]),
            "max_age_days": profile["max_age_days"] or 0,
        }
    return {
        "profile_id": None,
        "name": "default",
        "requirements": "",
        "keywords_include": "",
        "keywords_exclude": "",
        "min_salary": 0,
        "salary_filter_enabled": False,
        "max_age_days": 0,
    }


def _keywords_to_req(include: str, exclude: str) -> str:
    parts = []
    for word in include.split(","):
        word = word.strip()
        if word:
            parts.append(f"+{word}")
    for word in exclude.split(","):
        word = word.strip()
        if word:
            parts.append(f"-{word}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Legacy filters — теперь работают с активным профилем
# ---------------------------------------------------------------------------
async def set_requirements(user_id: int, raw: str) -> None:
    """Сохраняет +word -word в активный профиль."""
    from filters import RequirementFilter

    filt = RequirementFilter.parse(raw)
    profile = await get_active_profile(user_id)
    if profile:
        await update_profile(
            profile["id"],
            keywords_include=",".join(filt.include),
            keywords_exclude=",".join(filt.exclude),
        )
    else:
        pid = await create_profile(user_id, "default")
        await update_profile(
            pid,
            keywords_include=",".join(filt.include),
            keywords_exclude=",".join(filt.exclude),
        )


async def get_requirements(user_id: int) -> str:
    filters = await get_active_filters(user_id)
    return filters["requirements"]


async def set_min_salary(user_id: int, amount: int) -> None:
    profile = await get_active_profile(user_id)
    if profile:
        await update_profile(profile["id"], min_salary=amount)
    else:
        pid = await create_profile(user_id, "default")
        await update_profile(pid, min_salary=amount)


async def get_min_salary(user_id: int) -> int:
    filters = await get_active_filters(user_id)
    return filters["min_salary"]


async def set_salary_filter(user_id: int, enabled: bool) -> None:
    profile = await get_active_profile(user_id)
    if profile:
        await update_profile(profile["id"], salary_filter_on=int(enabled))
    else:
        pid = await create_profile(user_id, "default")
        await update_profile(pid, salary_filter_on=int(enabled))


async def is_salary_filter_enabled(user_id: int) -> bool:
    filters = await get_active_filters(user_id)
    return filters["salary_filter_enabled"]


async def set_max_age_days(user_id: int, days: int) -> None:
    profile = await get_active_profile(user_id)
    if profile:
        await update_profile(profile["id"], max_age_days=days)
    else:
        pid = await create_profile(user_id, "default")
        await update_profile(pid, max_age_days=days)


async def get_max_age_days(user_id: int) -> int:
    filters = await get_active_filters(user_id)
    return filters["max_age_days"]
