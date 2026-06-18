"""Управление каналами."""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import add_channel, remove_channel
from keyboards.main import back_to_menu
from utils.helpers import parse_channel_username

router = Router()


class AddChannelState(StatesGroup):
    waiting_for_link = State()


async def _try_add_channel(text: str) -> tuple[str, str]:
    username = parse_channel_username(text)
    if not username:
        return (
            "",
            "❌ Не удалось распознать канал. Пришли ссылку вида "
            "<code>https://t.me/channelname</code> или <code>@channelname</code>",
        )
    ok = await add_channel(username)
    if ok:
        return username, f"✅ Канал @{username} добавлен в список отслеживания."
    return username, f"⚠️ Канал @{username} уже в списке или имя некорректно."


@router.message(Command("addchannel"))
async def cmd_add_channel(message: types.Message, state: FSMContext) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) >= 2:
        _, reply = await _try_add_channel(args[1])
        await message.answer(reply, parse_mode=ParseMode.HTML)
        return

    await state.set_state(AddChannelState.waiting_for_link)
    await message.answer(
        "📎 Пришли ссылку на Telegram-канал или его @username.\n\n"
        "Примеры:\n"
        "<code>https://t.me/channelname</code>\n"
        "<code>@channelname</code>",
        parse_mode=ParseMode.HTML,
    )


@router.message(AddChannelState.waiting_for_link)
async def process_channel_link(message: types.Message, state: FSMContext) -> None:
    _, reply = await _try_add_channel(message.text or "")
    await state.clear()
    await message.answer(reply, parse_mode=ParseMode.HTML, reply_markup=back_to_menu())


@router.callback_query(F.data == "add_channel")
async def cb_add_channel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChannelState.waiting_for_link)
    await callback.message.answer(
        "📎 Пришли ссылку на Telegram-канал или его @username.\n\n"
        "Примеры:\n"
        "<code>https://t.me/channelname</code>\n"
        "<code>@channelname</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(Command("removechannel"))
async def cmd_remove_channel(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажи канал: /removechannel @channelname")
        return

    username = parse_channel_username(args[1])
    ok = await remove_channel(username)
    if ok:
        await message.answer(f"✅ Канал @{username} удалён.")
    else:
        await message.answer(f"⚠️ Канал @{username} не найден.")


@router.message(Command("channels"))
async def cmd_channels(message: types.Message) -> None:
    from database import list_channels as db_list_channels

    channels = await db_list_channels()
    if not channels:
        await message.answer(
            "📭 Пока нет отслеживаемых каналов. Добавь: /addchannel @channel",
            reply_markup=back_to_menu(),
        )
        return

    lines = ["📡 Отслеживаемые каналы:"]
    for ch in channels:
        title = ch.get("title") or ""
        line = f"• @{ch['username']}"
        if title:
            line += f" — {title}"
        lines.append(line)

    await message.answer("\n".join(lines), reply_markup=back_to_menu())
