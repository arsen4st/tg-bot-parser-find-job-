"""Точка входа: запускает бота и парсер в одном event loop."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from telethon import TelegramClient

import config
from bot import start_bot, stop_bot
from handlers.vacancies import send_vacancy
from database import add_channel, init_db
from parser import VacancyParser, register_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not config.BOT_TOKEN or config.BOT_TOKEN == "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz":
        logger.error("BOT_TOKEN не настроен. Заполни .env файл.")
        sys.exit(1)

    if config.API_ID == 0 or not config.API_HASH:
        logger.error("API_ID/API_HASH не настроены. Заполни .env файл.")
        sys.exit(1)

    await init_db()
    logger.info("База данных инициализирована")

    # Добавляем каналы по умолчанию из .env
    for channel in config.DEFAULT_CHANNELS:
        await add_channel(channel)
        logger.info("Канал по умолчанию добавлен: %s", channel)

    # Проверяем, авторизован ли Telethon
    is_authorized = await _check_telethon_auth()

    if not is_authorized:
        logger.warning("Telethon не авторизован. Запускаю только бота.")
        logger.warning("Отправь боту команду /login, отсканируй QR-код и перезапусти main.py")
        try:
            await start_bot()
        finally:
            await stop_bot()
        return

    parser = VacancyParser(callback=send_vacancy)
    register_parser(parser)
    await parser.start()

    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(parser)))
    except NotImplementedError:
        # Windows не поддерживает add_signal_handler
        logger.warning("Обработка сигналов не поддерживается на Windows.")

    logger.info("Бот и парсер запущены. Нажми Ctrl+C для остановки.")
    try:
        await asyncio.gather(
            start_bot(),
            parser.run_until_disconnected(),
        )
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки.")
    finally:
        await _shutdown(parser)


async def _check_telethon_auth() -> bool:
    """Проверяет, авторизован ли пользователь в Telethon."""
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    try:
        await client.connect()
        return await client.is_user_authorized()
    finally:
        await client.disconnect()


async def _shutdown(parser: VacancyParser) -> None:
    logger.info("Остановка...")
    await parser.stop()
    await stop_bot()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Остановлено.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
