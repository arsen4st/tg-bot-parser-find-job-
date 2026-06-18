"""Управление профилями поиска."""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    create_profile,
    delete_profile,
    get_active_profile,
    get_profile,
    list_profiles,
    set_active_profile,
    update_profile,
)
from keyboards.main import (
    back_to_menu,
    confirm_delete_profile,
    profile_filters_menu,
    profile_menu,
    profiles_list,
)
from parser import invalidate_parser_cache
from utils.helpers import escape_html

router = Router()


class ProfileState(StatesGroup):
    waiting_profile_name = State()
    waiting_keywords_include = State()
    waiting_keywords_exclude = State()
    waiting_min_salary = State()
    waiting_max_age = State()


# ---------------------------------------------------------------------------
# /profiles
# ---------------------------------------------------------------------------
@router.message(Command("profiles"))
async def cmd_profiles(message: types.Message) -> None:
    await _show_profiles(message)


@router.callback_query(F.data == "profiles")
async def cb_profiles(callback: types.CallbackQuery) -> None:
    await _show_profiles(callback.message)
    await callback.answer()


async def _show_profiles(target: types.Message) -> None:
    profiles = await list_profiles(target.from_user.id)
    if not profiles:
        await target.answer(
            "👤 У тебя пока нет профилей. Создай первый через /newprofile",
            reply_markup=back_to_menu(),
        )
        return
    active = await get_active_profile(target.from_user.id)
    active_name = active["name"] if active else "нет"
    await target.answer(
        f"👤 Твои профили. Активен: <b>{escape_html(active_name)}</b>\n\n"
        f"Нажми на профиль, чтобы активировать или настроить:",
        parse_mode=ParseMode.HTML,
        reply_markup=profiles_list(profiles),
    )


# ---------------------------------------------------------------------------
# /newprofile
# ---------------------------------------------------------------------------
@router.message(Command("newprofile"))
async def cmd_new_profile(message: types.Message, state: FSMContext) -> None:
    await state.set_state(ProfileState.waiting_profile_name)
    await message.answer(
        "📝 Введи название нового профиля.\n\n"
        "Примеры: <code>Python джун</code>, <code>React удалённо</code>",
        parse_mode=ParseMode.HTML,
    )


@router.message(ProfileState.waiting_profile_name)
async def process_profile_name(message: types.Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Попробуй ещё раз.")
        return

    profile_id = await create_profile(message.from_user.id, name)
    invalidate_parser_cache()
    await state.clear()

    await message.answer(
        f"✅ Создан и активирован профиль: <b>{escape_html(name)}</b>\n\n"
        f"Теперь задай фильтры через /setreq или в настройках профиля.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu(),
    )


@router.callback_query(F.data == "new_profile")
async def cb_new_profile(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileState.waiting_profile_name)
    await callback.message.answer(
        "📝 Введи название нового профиля.\n\n"
        "Примеры: <code>Python джун</code>, <code>React удалённо</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Меню профиля
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("profile_menu:"))
async def cb_profile_menu(callback: types.CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("❌ Профиль не найден.", show_alert=True)
        return

    text = (
        f"👤 <b>{escape_html(profile['name'])}</b>\n"
        f"{'✅ Активен' if profile['is_active'] else '⏸ Не активен'}\n\n"
        f"<b>Включить:</b> {profile['keywords_include'] or '—'}\n"
        f"<b>Исключить:</b> {profile['keywords_exclude'] or '—'}\n"
        f"<b>Мин. зарплата:</b> {profile['min_salary'] if profile['salary_filter_on'] else 'выкл'}\n"
        f"<b>Макс. возраст:</b> {profile['max_age_days'] if profile['max_age_days'] else 'не задан'}"
    )
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=profile_menu(profile_id, bool(profile["is_active"])),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Активация профиля
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("activate_profile:"))
async def cb_activate_profile(callback: types.CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    ok = await set_active_profile(callback.from_user.id, profile_id)
    if not ok:
        await callback.answer("❌ Не удалось активировать профиль.", show_alert=True)
        return

    invalidate_parser_cache()
    profile = await get_profile(profile_id)
    await callback.message.answer(
        f"✅ Активирован профиль: <b>{escape_html(profile['name'])}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Редактирование фильтров профиля
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("edit_profile:"))
async def cb_edit_profile(callback: types.CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "⚙️ Выбери, что отредактировать:",
        reply_markup=profile_filters_menu(profile_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_include:"))
async def cb_edit_include(callback: types.CallbackQuery, state: FSMContext) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ProfileState.waiting_keywords_include)
    await state.update_data(profile_id=profile_id)
    await callback.message.answer(
        "📝 Введи слова, которые <b>должны быть</b> в вакансии, через запятую.\n\n"
        "Пример: <code>python, django, junior</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(ProfileState.waiting_keywords_include)
async def process_keywords_include(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id = data["profile_id"]
    value = (message.text or "").strip().lower()
    await update_profile(profile_id, keywords_include=value)
    invalidate_parser_cache()
    await state.clear()
    await message.answer(
        "✅ Ключевые слова для включения обновлены.",
        reply_markup=profile_filters_menu(profile_id),
    )


@router.callback_query(F.data.startswith("edit_exclude:"))
async def cb_edit_exclude(callback: types.CallbackQuery, state: FSMContext) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ProfileState.waiting_keywords_exclude)
    await state.update_data(profile_id=profile_id)
    await callback.message.answer(
        "📝 Введи слова, которые <b>не должны быть</b> в вакансии, через запятую.\n\n"
        "Пример: <code>senior, lead, опыт 5 лет</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(ProfileState.waiting_keywords_exclude)
async def process_keywords_exclude(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id = data["profile_id"]
    value = (message.text or "").strip().lower()
    await update_profile(profile_id, keywords_exclude=value)
    invalidate_parser_cache()
    await state.clear()
    await message.answer(
        "✅ Стоп-слова обновлены.",
        reply_markup=profile_filters_menu(profile_id),
    )


@router.callback_query(F.data.startswith("edit_salary:"))
async def cb_edit_salary(callback: types.CallbackQuery, state: FSMContext) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ProfileState.waiting_min_salary)
    await state.update_data(profile_id=profile_id)
    await callback.message.answer(
        "💰 Введи минимальную зарплату числом (0 = выключить фильтр).\n\n"
        "Пример: <code>50000</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(ProfileState.waiting_min_salary)
async def process_min_salary(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id = data["profile_id"]
    try:
        value = int(message.text.strip().replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Нужно число. Попробуй ещё раз.")
        return

    await update_profile(
        profile_id,
        min_salary=value,
        salary_filter_on=1 if value > 0 else 0,
    )
    invalidate_parser_cache()
    await state.clear()
    status = "включён" if value > 0 else "выключен"
    await message.answer(
        f"✅ Минимальная зарплата {status}: {value}",
        reply_markup=profile_filters_menu(profile_id),
    )


@router.callback_query(F.data.startswith("edit_age:"))
async def cb_edit_age(callback: types.CallbackQuery, state: FSMContext) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ProfileState.waiting_max_age)
    await state.update_data(profile_id=profile_id)
    await callback.message.answer(
        "📅 Введи максимальный возраст вакансии в днях (0 = не проверять).\n\n"
        "Пример: <code>7</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(ProfileState.waiting_max_age)
async def process_max_age(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    profile_id = data["profile_id"]
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Нужно число. Попробуй ещё раз.")
        return

    await update_profile(profile_id, max_age_days=max(value, 0))
    invalidate_parser_cache()
    await state.clear()
    await message.answer(
        f"✅ Максимальный возраст: {value} дней." if value > 0 else "✅ Проверка возраста отключена.",
        reply_markup=profile_filters_menu(profile_id),
    )


# ---------------------------------------------------------------------------
# Удаление профиля
# ---------------------------------------------------------------------------
@router.message(Command("deleteprofile"))
async def cmd_delete_profile(message: types.Message) -> None:
    profiles = await list_profiles(message.from_user.id)
    if not profiles:
        await message.answer("❌ У тебя нет профилей для удаления.")
        return
    text = "Выбери профиль для удаления:\n\n⚠️ Активный профиль удалить нельзя."
    await message.answer(text, reply_markup=profiles_list(profiles))


@router.callback_query(F.data.startswith("delete_profile:"))
async def cb_delete_profile(callback: types.CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("❌ Профиль не найден.", show_alert=True)
        return
    if profile.get("is_active"):
        await callback.answer("❌ Нельзя удалить активный профиль.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 Точно удалить профиль <b>{escape_html(profile['name'])}</b>?",
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_delete_profile(profile_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_profile:"))
async def cb_confirm_delete_profile(callback: types.CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    profile = await get_profile(profile_id)
    if not profile:
        await callback.answer("❌ Профиль не найден.", show_alert=True)
        return
    if profile.get("is_active"):
        await callback.answer("❌ Нельзя удалить активный профиль.", show_alert=True)
        return

    ok = await delete_profile(profile_id)
    if ok:
        await callback.message.answer(
            f"✅ Профиль <b>{escape_html(profile['name'])}</b> удалён.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu(),
        )
    else:
        await callback.message.answer("❌ Не удалось удалить профиль.")
    await callback.answer()
