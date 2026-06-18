"""Избранные вакансии."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from database import (
    get_saved,
    get_saved_count,
    remove_saved,
    update_saved_status,
)
from keyboards.main import back_to_menu, saved_list_keyboard, saved_vacancy_actions_keyboard
from utils.formatter import format_vacancy

logger = logging.getLogger(__name__)
router = Router()

PER_PAGE = 5

_STATUS_LABELS = {
    "saved": "Сохранено",
    "applied": "Откликнулся",
    "rejected": "Отклонено",
}


def _status_badge(status: str) -> str:
    badges = {
        "saved": "🔖",
        "applied": "✅",
        "rejected": "❌",
    }
    return badges.get(status, "🔖")


def _iso_to_datetime(iso_string: str | None) -> datetime | None:
    if not iso_string:
        return None
    try:
        dt = datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


async def _send_saved_list(
    target: types.Message,
    user_id: int,
    offset: int = 0,
    status: str | None = None,
) -> None:
    total = await get_saved_count(user_id, status=status)

    if total == 0:
        await target.answer(
            "Пока ничего не сохранено. Нажми ❤️ под любой вакансией.",
            reply_markup=back_to_menu(),
        )
        return

    items = await get_saved(user_id, status=status, limit=PER_PAGE, offset=offset)

    if not items and offset > 0:
        await _send_saved_list(target, user_id, offset=0, status=status)
        return

    for item in items:
        date = _iso_to_datetime(item.get("saved_at"))
        text = format_vacancy(
            item["text"],
            item["channel"],
            item["url"],
            date,
        )
        text += f"\n\n{_status_badge(item['status'])} Статус: {_STATUS_LABELS.get(item['status'], item['status'])}"
        await target.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=saved_vacancy_actions_keyboard(item["id"], item["url"]),
            disable_web_page_preview=True,
        )

    await target.answer(
        f"Страница {offset // PER_PAGE + 1} / {(total + PER_PAGE - 1) // PER_PAGE}",
        reply_markup=saved_list_keyboard(offset, total, status=status, per_page=PER_PAGE),
    )


async def _edit_saved_list(
    message: types.Message,
    user_id: int,
    offset: int = 0,
    status: str | None = None,
) -> None:
    total = await get_saved_count(user_id, status=status)

    if total == 0:
        await message.edit_text(
            "Пока ничего не сохранено. Нажми ❤️ под любой вакансией.",
            reply_markup=back_to_menu(),
        )
        return

    items = await get_saved(user_id, status=status, limit=PER_PAGE, offset=offset)

    if not items and offset > 0:
        await _edit_saved_list(message, user_id, offset=0, status=status)
        return

    # При редактировании пересылаем заново не получится — заменим на текстовую сводку
    text = f"❤️ Сохранённые вакансии ({_STATUS_LABELS.get(status, 'все')}):\n\n"
    for item in items:
        date = _iso_to_datetime(item.get("saved_at"))
        card = format_vacancy(item["text"], item["channel"], item["url"], date)
        text += card + f"\n{_status_badge(item['status'])} Статус: {_STATUS_LABELS.get(item['status'], item['status'])}\n\n"

    await message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=saved_list_keyboard(offset, total, status=status, per_page=PER_PAGE),
    )


@router.message(Command("saved"))
async def cmd_saved(message: types.Message) -> None:
    await _send_saved_list(message, message.from_user.id)


@router.callback_query(F.data == "saved")
async def cb_saved(callback: types.CallbackQuery) -> None:
    await _send_saved_list(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("saved_page:"))
async def cb_saved_page(callback: types.CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        offset = int(parts[1])
        status = parts[2] if len(parts) > 2 and parts[2] != "all" else None
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка навигации.", show_alert=True)
        return

    await _edit_saved_list(callback.message, callback.from_user.id, offset=offset, status=status)
    await callback.answer()


@router.callback_query(F.data.startswith("saved_filter:"))
async def cb_saved_filter(callback: types.CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        status = parts[1] if len(parts) > 1 else "all"
        status = None if status == "all" else status
    except IndexError:
        status = None

    await _edit_saved_list(callback.message, callback.from_user.id, offset=0, status=status)
    await callback.answer()


@router.callback_query(F.data.startswith("saved_status:"))
async def cb_saved_status(callback: types.CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        saved_id = int(parts[1])
        new_status = parts[2]
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка.", show_alert=True)
        return

    ok = await update_saved_status(saved_id, new_status)
    if not ok:
        await callback.answer("❌ Вакансия не найдена.", show_alert=True)
        return

    offset, status = _extract_offset_status(callback.message.reply_markup)
    await _edit_saved_list(callback.message, callback.from_user.id, offset=offset, status=status)
    await callback.answer(f"Статус: {_STATUS_LABELS.get(new_status, new_status)} ✅")


@router.callback_query(F.data.startswith("saved_delete:"))
async def cb_saved_delete(callback: types.CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        saved_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка.", show_alert=True)
        return

    ok = await remove_saved(saved_id)
    if not ok:
        await callback.answer("❌ Вакансия не найдена.", show_alert=True)
        return

    offset, status = _extract_offset_status(callback.message.reply_markup)
    await _edit_saved_list(callback.message, callback.from_user.id, offset=offset, status=status)
    await callback.answer("Удалено из избранного")


def _extract_offset_status(reply_markup) -> tuple[int, str | None]:
    offset = 0
    status = None
    if reply_markup:
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("saved_page:"):
                    pp = btn.callback_data.split(":")
                    try:
                        offset = int(pp[1])
                        status = pp[2] if len(pp) > 2 and pp[2] != "all" else None
                    except (ValueError, IndexError):
                        pass
                    break
    return offset, status
