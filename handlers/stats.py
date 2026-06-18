"""Статистика по найденным вакансиям."""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from database import get_stats_by_channels, get_stats_by_days, get_stats_total
from keyboards.main import stats_keyboard

router = Router()

_MONTHS_RU = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}


def _format_date_ru(date_str: str) -> str:
    """2025-06-18 → 18 июн."""
    from datetime import datetime

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {_MONTHS_RU.get(dt.month, '')}"


def _progress_bar(value: int, max_value: int, length: int = 10) -> str:
    if max_value == 0:
        return "░" * length
    filled = int(round(value / max_value * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


def _format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")


async def _build_stats_text(user_id: int, days: int = 7) -> str:
    total_stats = await get_stats_total(user_id)

    if total_stats["total_found"] == 0:
        return "📊 *Статистика поиска*\n\nПока вакансий нет. Добавь каналы через /addchannel"

    by_days = await get_stats_by_days(user_id, days)
    by_channels = await get_stats_by_channels(user_id, limit=10)

    max_day_count = max((d["count"] for d in by_days), default=0)

    lines = [
        "📊 *Статистика поиска*",
        "",
        f"*Всего найдено:* {_format_number(total_stats['total_found'])} вакансий",
        f"*Сегодня:* {_format_number(total_stats['today'])}",
        f"*За 7 дней:* {_format_number(total_stats['this_week'])}",
        f"*В среднем в день:* {total_stats['avg_per_day']}",
        f"*Прошло фильтров:* {_format_number(total_stats['passed_filters'])}",
        "",
        f"*По дням (последние {days}):*",
    ]

    for d in by_days:
        bar = _progress_bar(d["count"], max_day_count)
        date_ru = _format_date_ru(d["date"])
        lines.append(f"`{date_ru:<6}` `{bar}` `{_format_number(d['count']):>5}`")

    if by_channels:
        lines.append("")
        lines.append("*Топ каналов:*")
        for i, ch in enumerate(by_channels, 1):
            username = ch["channel"]
            count = ch["count"]
            lines.append(f"{i}. `@{username:<20}` — {_format_number(count)}")

    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    text = await _build_stats_text(message.from_user.id)
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=stats_keyboard(days=7),
    )


@router.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery) -> None:
    text = await _build_stats_text(callback.from_user.id)
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=stats_keyboard(days=7),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stats_days:"))
async def cb_stats_days(callback: types.CallbackQuery) -> None:
    days = int(callback.data.split(":", 1)[1])
    text = await _build_stats_text(callback.from_user.id, days=days)
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=stats_keyboard(days=days),
    )
    await callback.answer()


@router.callback_query(F.data == "stats_refresh")
async def cb_stats_refresh(callback: types.CallbackQuery) -> None:
    text = await _build_stats_text(callback.from_user.id, days=7)
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=stats_keyboard(days=7),
    )
    await callback.answer("🔄 Обновлено")
