"""Управление фильтрами требований."""

from __future__ import annotations

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from database import get_requirements, set_requirements
from filters import RequirementFilter
from keyboards.main import back_to_menu

router = Router()


@router.message(Command("setreq"))
async def cmd_set_req(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажи требования. Пример:\n"
            "<code>/setreq +python +удалённо -senior -опыт</code>\n\n"
            "<code>+</code> — обязательно есть\n"
            "<code>-</code> — исключить",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = args[1]
    filt = RequirementFilter.parse(raw)
    if filt.is_empty():
        await message.answer("❌ Не найдено слов с + или -. Попробуй ещё раз.")
        return

    await set_requirements(message.from_user.id, raw)
    inc = ", ".join(f"+{w}" for w in filt.include) or "—"
    exc = ", ".join(f"-{w}" for w in filt.exclude) or "—"
    await message.answer(
        f"✅ Фильтр обновлён!\n"
        f"<b>Включить:</b> {inc}\n"
        f"<b>Исключить:</b> {exc}",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu(),
    )


@router.message(Command("requirements"))
async def cmd_requirements(message: types.Message) -> None:
    req = await get_requirements(message.from_user.id)
    if not req:
        await message.answer(
            "🔧 Требования не заданы.\n"
            "Пример: <code>/setreq +python +удалённо -senior</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    filt = RequirementFilter.parse(req)
    inc = ", ".join(f"+{w}" for w in filt.include) or "—"
    exc = ", ".join(f"-{w}" for w in filt.exclude) or "—"
    await message.answer(
        f"🔧 Текущие требования:\n"
        f"<b>Включить:</b> {inc}\n"
        f"<b>Исключить:</b> {exc}",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(lambda c: c.data == "set_filter")
async def cb_set_filter(callback: types.CallbackQuery) -> None:
    await callback.message.answer(
        "Напиши фильтр командой:\n<code>/setreq +python +удалённо -senior</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
