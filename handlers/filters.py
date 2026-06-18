"""Управление фильтрами требований, зарплаты и актуальности."""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command

from database import (
    get_max_age_days,
    get_min_salary,
    get_requirements,
    is_salary_filter_enabled,
    set_max_age_days,
    set_min_salary,
    set_requirements,
    set_salary_filter,
)
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
    min_salary = await get_min_salary(message.from_user.id)
    salary_enabled = await is_salary_filter_enabled(message.from_user.id)
    max_age = await get_max_age_days(message.from_user.id)

    lines = ["🔧 Текущие настройки фильтра:\n"]
    lines.append(f"<b>Требования:</b> {req or 'не заданы'}")
    lines.append(f"<b>Мин. зарплата:</b> {min_salary if salary_enabled else 'выкл'}")
    lines.append(f"<b>Макс. возраст:</b> {max_age if max_age > 0 else 'не задан'}")

    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu(),
    )


@router.message(Command("setminsalary"))
async def cmd_set_min_salary(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажи сумму. Пример:\n"
            "<code>/setminsalary 50000</code>\n\n"
            "После этого включи фильтр: <code>/salaryfilter on</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        amount = int(args[1].replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Нужно число. Пример: <code>/setminsalary 50000</code>")
        return

    await set_min_salary(message.from_user.id, amount)
    await message.answer(
        f"✅ Минимальная зарплата: {amount}.\n"
        f"Включи фильтр: <code>/salaryfilter on</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu(),
    )


@router.message(Command("salaryfilter"))
async def cmd_salary_filter(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        await message.answer(
            "❌ Укажи <code>on</code> или <code>off</code>.\n"
            "Пример: <code>/salaryfilter on</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    enabled = args[1].lower() == "on"
    await set_salary_filter(message.from_user.id, enabled)
    status = "включен ✅" if enabled else "выключен ❌"
    await message.answer(f"Фильтр по зарплате {status}.", reply_markup=back_to_menu())


@router.message(Command("setmaxage"))
async def cmd_set_max_age(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажи количество дней. Пример:\n"
            "<code>/setmaxage 7</code> — показывать вакансии не старше 7 дней\n"
            "<code>/setmaxage 0</code> — отключить проверку",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        days = int(args[1])
    except ValueError:
        await message.answer("❌ Нужно число.")
        return

    await set_max_age_days(message.from_user.id, max(days, 0))
    await message.answer(
        f"✅ Максимальный возраст вакансии: {days} дней."
        if days > 0
        else "✅ Проверка возраста отключена.",
        reply_markup=back_to_menu(),
    )


@router.callback_query(F.data == "set_filter")
async def cb_set_filter(callback: types.CallbackQuery) -> None:
    await callback.message.answer(
        "Напиши фильтр командой:\n<code>/setreq +python +удалённо -senior</code>\n\n"
        "Дополнительно:\n"
        "<code>/setminsalary 50000</code>\n"
        "<code>/salaryfilter on</code>\n"
        "<code>/setmaxage 7</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
