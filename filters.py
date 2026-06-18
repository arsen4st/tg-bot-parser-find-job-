"""Фильтрация и ранжирование вакансий."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Базовые маркеры вакансий — помогают отсеять мусор
core_vacancy_keywords = {
    "вакансия", "требуется", "ищем", "набираем", "открыта", "вакансии",
    "зарплата", "зп", "доход", "оплата", "ставка", "удаленно", "remote",
    "офис", "график", "опыт", "resume", "резюме", "контакты", "телеграм",
}


@dataclass
class RequirementFilter:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, raw: str) -> "RequirementFilter":
        """
        Парсит строку вида '+python +удалённо -senior -опыт'.
        Слова без знака игнорируются.
        """
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
        """
        Возвращает (matched, score).
        matched = True, если есть включения (или фильтр пуст) и нет исключений.
        score чем выше, тем релевантнее вакансия.
        """
        text = text.lower()
        words = set(re.findall(r"[a-zа-яё0-9]+", text))

        # Если текст совсем не похож на вакансию — понижаем
        core_hits = sum(1 for kw in core_vacancy_keywords if kw in text)
        score = float(core_hits) * 0.1

        if self.is_empty():
            # Без фильтра берём всё, что похоже на вакансию
            return core_hits >= 1, score

        # Проверяем исключения — если хоть одно найдено, вакансия не подходит
        for ex in self.exclude:
            if self._word_present(ex, words, text):
                return False, -1.0

        include_score = 0.0
        for inc in self.include:
            if self._word_present(inc, words, text):
                include_score += 1.0
            elif inc in text:
                # Частичное вхождение
                include_score += 0.5

        matched = include_score > 0
        score += include_score
        return matched, score

    @staticmethod
    def _word_present(needle: str, words: set[str], text: str) -> bool:
        if needle in words:
            return True
        # Регулярка для границ слов, чтобы "python" не ловило "pythonist" на 100%
        pattern = r"(?:^|[\s\W])" + re.escape(needle) + r"(?:[\s\W]|$)"
        return bool(re.search(pattern, text, flags=re.IGNORECASE))


def is_likely_vacancy(text: str) -> bool:
    """Быстрая проверка, похож ли пост на вакансию."""
    text = text.lower()
    return any(kw in text for kw in core_vacancy_keywords)
