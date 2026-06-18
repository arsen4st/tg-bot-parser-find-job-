"""Форматирование карточек вакансий."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Regex для парсинга зарплаты
# ---------------------------------------------------------------------------
SALARY_CURRENCY_MAP = {
    "сом": "сом",
    "kgs": "KGS",
    "руб": "руб",
    "рубль": "руб",
    "rub": "RUB",
    "$": "$",
    "usd": "USD",
    "доллар": "$",
    "тенге": "KZT",
    "kzt": "KZT",
}

CURRENCY_SYMBOLS = r"(?:\$|сом|kgs|руб|рубль|rub|usd|доллар|тенге|kzt)"

_RE_SALARY_RANGE = re.compile(
    rf"(?P<cur_a>{CURRENCY_SYMBOLS})?\s*(?P<a>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))\s*[-—]\s*(?P<cur_b>{CURRENCY_SYMBOLS})?\s*(?P<b>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))\s*(?P<cur>{CURRENCY_SYMBOLS})?",
    re.IGNORECASE,
)

_RE_SALARY_FROM = re.compile(
    rf"(?:от|from|starting)\s+(?P<a>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))(?:\s*(?:до|to|-)\s*(?P<b>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b)))?\s*(?P<cur>{CURRENCY_SYMBOLS})?",
    re.IGNORECASE,
)

_RE_SALARY_TO = re.compile(
    rf"(?:до|to|up\s+to)\s+(?P<b>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))\s*(?P<cur>{CURRENCY_SYMBOLS})?",
    re.IGNORECASE,
)

_RE_SALARY_LABEL = re.compile(
    rf"(?:зарплата|зп|з/п|оклад|ставка|salary|оплата)\s*[:\-=]?\s*(?P<a>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))(?:\s*[-—]\s*(?P<b>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b)))?\s*(?P<cur>{CURRENCY_SYMBOLS})?",
    re.IGNORECASE,
)

_RE_SALARY_RAW_NUMBER = re.compile(
    rf"(?P<a>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))\s*(?P<cur>{CURRENCY_SYMBOLS})",
    re.IGNORECASE,
)

_RE_SALARY_CURRENCY_FIRST = re.compile(
    rf"(?P<cur>{CURRENCY_SYMBOLS})\s*(?P<a>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b))(?:\s*[-—]\s*(?P<b>[0-9]+(?:\s?[0-9]+)*(?:[кk]|\b)))?",
    re.IGNORECASE,
)

_RE_K_SUFFIX = re.compile(r"([0-9]+)\s*[кk]\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Regex для тегов
# ---------------------------------------------------------------------------
_RE_HASHTAG = re.compile(r"#([a-zA-Zа-яА-ЯёЁ0-9_]+)")

AUTO_TAGS = [
    (re.compile(r"\b(удал[её]нно|remote|дистанционно|удал[её]нк[ауо])\b", re.IGNORECASE), "🏠 Удалённо"),
    (re.compile(r"\b(офис|в\s+офисе|office)\b", re.IGNORECASE), "🏢 Офис"),
    (re.compile(r"\b(гибрид|hybrid)\b", re.IGNORECASE), "🔄 Гибрид"),
    (re.compile(r"\b(полная\s+занятость|full[\s\-]?time|фулл[\s\-]?тайм)\b", re.IGNORECASE), "⏰ Полная"),
    (re.compile(r"\b(частичная|неполная|part[\s\-]?time|парт[\s\-]?тайм)\b", re.IGNORECASE), "⏱ Частичная"),
    (re.compile(r"\b(стажировка|intern|стажёр|стажер)\b", re.IGNORECASE), "🎓 Стажировка"),
    (re.compile(r"\b(джун|junior|начинающ|jun)\b", re.IGNORECASE), "🟢 Junior"),
    (re.compile(r"\b(мидл|middle|mid)\b", re.IGNORECASE), "🟡 Middle"),
    (re.compile(r"\b(сеньор|senior|lead|лид|teamlead|team\s+lead)\b", re.IGNORECASE), "🔴 Senior"),
]

# ---------------------------------------------------------------------------
# Regex для заголовка
# ---------------------------------------------------------------------------
_RE_TITLE_PATTERN = re.compile(
    r"(?:ищем|требуется|нужен|нужна|открыта\s+вакансия|вакансия[:\-]?\s*)\s+(.+?)(?:\n|$|\.\s|\,\s|—)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _normalize_number(num_str: str) -> int:
    """'50 000', '50000', '50к' → 50000."""
    num_str = num_str.replace(" ", "").replace(",", "").replace(".", "")
    multiplier = 1
    if _RE_K_SUFFIX.search(num_str):
        num_str = _RE_K_SUFFIX.sub(r"\1", num_str)
        multiplier = 1000
    try:
        return int(num_str) * multiplier
    except ValueError:
        return 0


def _format_money(amount: int) -> str:
    """80000 → '80 000'."""
    return f"{amount:,}".replace(",", " ")


def _detect_currency(text: str, match_end: int) -> str | None:
    """Определяет валюту рядом с числом."""
    text_lower = text.lower()
    for word, symbol in SALARY_CURRENCY_MAP.items():
        if word in text_lower:
            return symbol
    # Ищем символ валюты рядом с match
    window = text[max(0, match_end - 15) : match_end + 15].lower()
    for word, symbol in SALARY_CURRENCY_MAP.items():
        if word in window:
            return symbol
    return None


def _escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Парсеры
# ---------------------------------------------------------------------------
def parse_salary(text: str | None) -> dict:
    """Ищет зарплату в тексте."""
    result = {"min": None, "max": None, "currency": None, "raw": None}
    if not text:
        return result

    text_lower = text.lower()
    if "договорная" in text_lower or "по договоренности" in text_lower:
        return result

    candidates = []

    patterns = (
        _RE_SALARY_RANGE,
        _RE_SALARY_FROM,
        _RE_SALARY_TO,
        _RE_SALARY_LABEL,
        _RE_SALARY_RAW_NUMBER,
        _RE_SALARY_CURRENCY_FIRST,
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            a = match.group("a") if "a" in match.groupdict() else None
            b = match.group("b") if "b" in match.groupdict() else None
            cur = match.group("cur") if "cur" in match.groupdict() and match.group("cur") else None
            cur_a = match.group("cur_a") if "cur_a" in match.groupdict() and match.group("cur_a") else None
            cur_b = match.group("cur_b") if "cur_b" in match.groupdict() and match.group("cur_b") else None

            min_val = _normalize_number(a) if a else None
            max_val = _normalize_number(b) if b else None

            detected_cur = cur or cur_b or cur_a
            if detected_cur:
                currency = SALARY_CURRENCY_MAP.get(detected_cur.lower(), detected_cur)
            else:
                currency = _detect_currency(text, match.end())

            if min_val and max_val and min_val > max_val:
                min_val, max_val = max_val, min_val

            if not min_val and not max_val:
                continue

            candidates.append({
                "min": min_val,
                "max": max_val,
                "currency": currency,
                "raw": match.group(0),
            })

    if not candidates:
        return result

    # Выбираем кандидата с наибольшим max или min
    best = max(candidates, key=lambda x: (x["max"] or x["min"] or 0, len(x["raw"])))
    return best


def _salary_str(salary: dict) -> str | None:
    """Форматирует salary dict в человекочитаемую строку."""
    if not salary or (salary["min"] is None and salary["max"] is None):
        return None

    cur = salary["currency"] or ""
    min_val = salary["min"]
    max_val = salary["max"]

    if min_val and max_val:
        return f"от {_format_money(min_val)} до {_format_money(max_val)} {cur}".strip()
    if min_val:
        return f"от {_format_money(min_val)} {cur}".strip()
    if max_val:
        return f"до {_format_money(max_val)} {cur}".strip()
    return None


def parse_tags(text: str | None) -> list[str]:
    """Извлекает хэштеги и авто-теги."""
    tags = []
    if not text:
        return tags

    # Хэштеги
    for tag in _RE_HASHTAG.findall(text):
        t = f"#{tag.lower()}"
        if t not in tags:
            tags.append(t)

    # Авто-теги
    for pattern, label in AUTO_TAGS:
        if pattern.search(text):
            if label not in tags:
                tags.append(label)
        if len(tags) >= 6:
            break

    return tags[:6]


def parse_title(text: str | None) -> str:
    """Находит заголовок вакансии."""
    if not text:
        return "Вакансия"

    first_line = text.split("\n")[0].strip()

    if len(first_line) <= 60 and not re.match(
        r"^(ищем|требуется|нужен|нужна|открыта\s+вакансия|вакансия[:\-]?\s*)",
        first_line,
        re.IGNORECASE,
    ):
        return first_line

    match = _RE_TITLE_PATTERN.search(text)
    if match:
        title = match.group(1).strip()
        if len(title) > 80:
            title = title[:77] + "..."
        return title

    if first_line:
        return first_line[:57] + "..." if len(first_line) > 60 else first_line

    return "Вакансия"


def format_time_ago(date: datetime | None) -> str:
    """Форматирует относительное время с учётом UTC+6 (Бишкек)."""
    if date is None:
        return "неизвестно"

    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    bishkek_tz = timezone(timedelta(hours=6))
    now_utc = datetime.now(tz=timezone.utc)
    date_bishkek = date.astimezone(bishkek_tz)
    now_bishkek = now_utc.astimezone(bishkek_tz)
    delta = now_utc - date

    if delta < timedelta(minutes=1):
        return "только что"

    if delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        suffix = _pluralize(minutes, "минута", "минуты", "минут")
        return f"{minutes} {suffix} назад"

    if delta < timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        suffix = _pluralize(hours, "час", "часа", "часов")
        return f"{hours} {suffix} назад"

    yesterday = (now_bishkek - timedelta(days=1)).date()
    if date_bishkek.date() == yesterday:
        return f"вчера в {date_bishkek.strftime('%H:%M')}"

    if date_bishkek.year == now_bishkek.year:
        return f"{date_bishkek.day} {_MONTHS_RU.get(date_bishkek.month)} в {date_bishkek.strftime('%H:%M')}"

    return f"{date_bishkek.day} {_MONTHS_RU.get(date_bishkek.month)} {date_bishkek.year}"


def _pluralize(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return few
    return many


_MONTHS_RU = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}


def _truncate_text(text: str, max_len: int = 350) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.strip() + "..."


def format_vacancy(text: str | None, channel: str, url: str, date: datetime | None) -> str:
    """Форматирует карточку вакансии в HTML."""
    if not text or not text.strip():
        title = "Вакансия"
        body = "Текст вакансии отсутствует."
    else:
        title = parse_title(text)
        body = _truncate_text(text.strip())

    salary = parse_salary(text)
    salary_line = _salary_str(salary)
    tags = parse_tags(text)
    time_ago = format_time_ago(date)

    lines = [
        f"<b>💼 {_escape_html(title)}</b>",
        "",
        _escape_html(body),
    ]

    if salary_line:
        lines.append("")
        lines.append(f"💰 {salary_line}")

    if tags:
        lines.append("")
        lines.append(" ".join(tags))

    lines.append("")
    lines.append(f"📢 @{_escape_html(channel)} · 🕐 {time_ago}")

    return "\n".join(lines)
