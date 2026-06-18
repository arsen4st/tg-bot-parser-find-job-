"""Инициализация Telegram-бота."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from handlers import admin, channels, filters, menu, profiles, vacancies
from middleware.admin import AdminMiddleware
from middleware.errors import setup_error_handler
from middleware.throttling import ThrottlingMiddleware

logger = logging.getLogger(__name__)

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Middleware
dp.message.middleware(AdminMiddleware())
dp.callback_query.middleware(AdminMiddleware())
dp.message.middleware(ThrottlingMiddleware(rate_limit=0.8))
dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.5))

# Роутеры
dp.include_router(menu.router)
dp.include_router(channels.router)
dp.include_router(filters.router)
dp.include_router(vacancies.router)
dp.include_router(profiles.router)
dp.include_router(admin.router)

# Глобальный обработчик ошибок
setup_error_handler(dp)


async def start_bot() -> None:
    await dp.start_polling(bot)


async def stop_bot() -> None:
    await bot.session.close()
