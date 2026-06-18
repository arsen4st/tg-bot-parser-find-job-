# 🚀 Rabota Parser — парсер вакансий из Telegram

Быстрый асинхронный парсер вакансий из Telegram-каналов. Сам следит за новыми постами, фильтрует по твоим требованиям, зарплате и актуальности, и шлёт в личку бота с кнопкой «Перейти» на конкретный пост.

## ⚡ Особенности

- **Максимальная скорость**: asyncio + Telethon в режиме реального времени.
- **Умный фильтр**: включи/исключи ключевые слова (`+python +удалённо -senior`).
- **Фильтр по зарплате**: задай минимальную сумму, бот отсеет всё, что ниже.
- **Проверка актуальности**: не показывать вакансии старше N дней.
- **Прямые ссылки**: каждая вакансия с кнопкой на конкретный пост.
- **Удобное управление каналами**: добавление по ссылке, удаление одним нажатием ❌.
- **Production-ready**: rate limiting, проверка админа, глобальный обработчик ошибок.
- **Лёгкий**: SQLite, работает на ноутбуке в фоне.

## 📦 Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## ⚙️ Настройка

1. Скопируй `.env.example` → `.env`.
2. Получи **BOT_TOKEN** у [@BotFather](https://t.me/BotFather).
3. Получи **API_ID** и **API_HASH** на [my.telegram.org/apps](https://my.telegram.org/apps).
4. Узнай свой Telegram ID у [@userinfobot](https://t.me/userinfobot) и впиши в `ADMIN_ID`.
5. Подпишись в Telegram на каналы, которые хочешь парсить.

## 🚀 Запуск

```bash
python main.py
```

Или запусти `start.bat` (с окном) / `start_background.vbs` (фоном, без окна).

### Авторизация

При первом запуске отправь боту `/login` — он пришлёт QR-код. Отсканируй:

```
Telegram → Настройки → Устройства → Подключить устройство → Сканировать QR
```

После успеха перезапусти `main.py`.

## 🤖 Команды бота

- `/start` — главное меню
- `/addchannel` — добавить канал по ссылке или @username
- `/channels` — список каналов с кнопками удаления
- `/removechannel <@channel>` — удалить канал
- `/setreq <+слово -слово>` — фильтр по требованиям
- `/requirements` — текущие настройки фильтра
- `/setminsalary 50000` — минимальная зарплата
- `/salaryfilter on/off` — включить/выключить фильтр по зарплате
- `/setmaxage 7` — максимальный возраст вакансии в днях (0 — отключить)
- `/latest [N]` — последние N вакансий
- `/pause` / `/resume` — пауза/старт рассылки
- `/status` — статус
- `/login` — авторизация через QR

### Примеры

```
/setreq +python +удалённо -senior
/setminsalary 50000
/salaryfilter on
/setmaxage 7
```

## 🏗 Архитектура

```
rabota/
├── handlers/       # Команды и callback
├── keyboards/      # Reply и inline клавиатуры
├── middleware/     # Админ, throttling, ошибки
├── utils/          # Утилиты
├── bot.py          # Инициализация бота
├── parser.py       # Telethon-клиент
├── database.py     # SQLite
├── config.py       # Конфиг
└── main.py         # Точка входа
```

## 🛡 Безопасность

- `.env` с токенами в `.gitignore`.
- Только `ADMIN_ID` может управлять ботом.
- Rate limiting защищает от спама.

## 📄 Лицензия

MIT
