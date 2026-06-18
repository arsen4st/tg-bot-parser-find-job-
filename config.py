"""Конфигурация проекта."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
API_ID: int = int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
SESSION_NAME: str = os.getenv("SESSION_NAME", "rabota_session")

DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "rabota.db"))

# Каналы по умолчанию можно задать через запятую в .env
DEFAULT_CHANNELS: list[str] = [
    c.strip() for c in os.getenv("DEFAULT_CHANNELS", "").split(",") if c.strip()
]

# Максимальная длина текста вакансии в сообщении бота
MAX_MESSAGE_LENGTH = 3800

# Сколько последних вакансий показывать по команде /latest
DEFAULT_LATEST_LIMIT = 10

# Минимальный скор для того, чтобы вакансия считалась подходящей
MIN_SCORE_THRESHOLD = 0.0
