"""Фильтрация и ранжирование вакансий."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Базовые маркеры вакансий — помогают отсеять мусор
core_vacancy_keywords = {
    "вакансия", "требуется", "ищем", "набираем", "открыта", "вакансии",
    "зарплата", "зп", "доход", "оплата", "ставка", "удаленно", "remote",
    "офис", "график", "опыт", "resume", "резюме", "контакты", "телеграм",
    "з/п", "зарплата", "оклад", "денег", "сом", "руб", "тенге", "usd", "$",
}

# Слова-маркеры, что рядом цифра — это зарплата
salary_markers = [
    "зарплата", "зп", "з/п", "оклад", "ставка", "доход", "оплата",
    "получаешь", "зарабатывать", "в месяц", "в неделю", "в день",
    "сом", "руб", "тенге", "kgs", "kzt", "rub", "usd", "$",
    "от", "до",
]


@dataclass
class RequirementFilter:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, raw: str) -> "RequirementFilter":
        """Парсит строку вида '+python +удалённо -senior -опыт'."""
        include: list[str] = []
        exclude: list[str] = []

        for token in raw.lower().split():
            token = token.strip(",.;:!?()")
            if token.startswith("+") and len(token) > 1:
                include.append(token[1:])
            elif token.startswith("-") and len(token) > 1:
                exclude.append(token[1:])

        return cls(include=include, exclude=exclude)

    def is_empty(self) -> bool:
        return not self.include and not self.exclude

    def match(self, text: str) -> tuple[bool, float]:
        """Возвращает (matched, score)."""
        text = text.lower()
        words = set(re.findall(r"[a-zа-яё0-9]+", text))

        core_hits = sum(1 for kw in core_vacancy_keywords if kw in text)
        score = float(core_hits) * 0.1

        if self.is_empty():
            return core_hits >= 1, score

        for ex in self.exclude:
            if self._word_present(ex, words, text):
                return False, -1.0

        include_score = 0.0
        for inc in self.include:
            if self._word_present(inc, words, text):
                include_score += 1.0
            elif inc in text:
                include_score += 0.5

        matched = include_score > 0
        score += include_score
        return matched, score

    @staticmethod
    def _word_present(needle: str, words: set[str], text: str) -> bool:
        if needle in words:
            return True
        pattern = r"(?:^[\s\W])" + re.escape(needle) + r"(?:[\s\W]|$)"
        return bool(re.search(pattern, text, flags=re.IGNORECASE))


def is_likely_vacancy(text: str) -> bool:
    """Быстрая проверка, похож ли пост на вакансию."""
    text = text.lower()
    return any(kw in text for kw in core_vacancy_keywords)


def extract_salary(text: str) -> int | None:
    """Пытается извлечь максимальную зарплату из текста вакансии."""
    text = text.lower()
    salaries: list[int] = []

    # Ищем числа рядом с маркерами зарплаты
    for marker in salary_markers:
        # шаблон: маркер + число (с возможными пробелами и суффиксами)
        pattern = re.compile(
            rf"(?:{re.escape(marker)})\s*[:\-]?\s*([0-9]+(?:\s*[0-9]+)*)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            num_str = match.group(1).replace(" ", "").replace(",", "")
            try:
                num = int(num_str)
                if 1000 <= num <= 10_000_000:
                    salaries.append(num)
            except ValueError:
                continue

    # Ищем диапазоны вида "от 30000 до 50000"
    range_pattern = re.compile(
        r"от\s*([0-9]+(?:\s*[0-9]+)*)\s*до\s*([0-9]+(?:\s*[0-9]+)*)",
        re.IGNORECASE,
    )
    for match in range_pattern.finditer(text):
        for group in (match.group(1), match.group(2)):
            num_str = group.replace(" ", "").replace(",", "")
            try:
                num = int(num_str)
                if 1000 <= num <= 10_000_000:
                    salaries.append(num)
            except ValueError:
                continue

    # Ищем числа с суффиксом "к" (тысяч) — 50к, 100к
    k_pattern = re.compile(r"([0-9]+)\s*[кk]\b", re.IGNORECASE)
    for match in k_pattern.finditer(text):
        try:
            num = int(match.group(1)) * 1000
            if 1000 <= num <= 10_000_000:
                salaries.append(num)
        except ValueError:
            continue

    if not salaries:
        return None
    return max(salaries)


def is_actual(message_date: datetime | None, max_age_days: int) -> bool:
    """Проверяет, не устарело ли сообщение."""
    if not message_date or max_age_days <= 0:
        return True
    now = datetime.now(tz=timezone.utc)
    age = (now - message_date).days
    return age <= max_age_days
