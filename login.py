"""Авторизация через QR-код (если SMS не приходит)."""

from __future__ import annotations

import asyncio

import qrcode
from telethon import TelegramClient

import config


async def main() -> None:
    client = TelegramClient(
        config.SESSION_NAME,
        config.API_ID,
        config.API_HASH,
    )
    await client.connect()

    if await client.is_user_authorized():
        print("✅ Уже авторизовано. Можно запускать main.py")
        await client.disconnect()
        return

    print("Генерирую QR-код...")
    qr_login = await client.qr_login()

    # Создаём QR-код
    img = qrcode.make(qr_login.url)
    img.save("qr_login.png")

    print("\n✅ QR-код сохранён в файл: qr_login.png")
    print("Открой эту картинку и отсканируй её в Telegram:")
    print("  Telegram → Настройки → Устройства → Подключить устройство → Сканировать QR\n")
    print("Жду сканирования...")

    await qr_login.wait()

    print("✅ Авторизация успешна! Теперь запускай main.py")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
