"""Тесты для utils/formatter.py."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from utils.formatter import (
    format_time_ago,
    format_vacancy,
    parse_salary,
    parse_tags,
    parse_title,
)


class TestParseSalary(unittest.TestCase):
    def test_salary_with_currency(self):
        text = "Вакансия python разработчик. Зарплата от 80000 до 120000 сом"
        result = parse_salary(text)
        self.assertEqual(result["min"], 80000)
        self.assertEqual(result["max"], 120000)
        self.assertEqual(result["currency"], "сом")
        self.assertIsNotNone(result["raw"])

    def test_salary_range_k_suffix(self):
        text = "Ищем разработчика. Зп 50к-80к руб"
        result = parse_salary(text)
        self.assertEqual(result["min"], 50000)
        self.assertEqual(result["max"], 80000)
        self.assertEqual(result["currency"], "руб")

    def test_no_salary(self):
        text = "Ищем активного стажёра. Зарплата договорная."
        result = parse_salary(text)
        self.assertIsNone(result["min"])
        self.assertIsNone(result["max"])
        self.assertIsNone(result["currency"])

    def test_dollar_salary(self):
        text = "Salary $500 - $1000"
        result = parse_salary(text)
        self.assertEqual(result["min"], 500)
        self.assertEqual(result["max"], 1000)
        self.assertEqual(result["currency"], "$")


class TestParseTags(unittest.TestCase):
    def test_hashtag(self):
        text = "Вакансия #python #удалёнка в Бишкеке"
        tags = parse_tags(text)
        self.assertIn("#python", tags)
        self.assertIn("#удалёнка", tags)

    def test_auto_tag_remote(self):
        text = "Ищем разработчика на удаленку, full time"
        tags = parse_tags(text)
        self.assertIn("🏠 Удалённо", tags)
        self.assertIn("⏰ Полная", tags)

    def test_no_duplicates(self):
        text = "#python python junior junior"
        tags = parse_tags(text)
        self.assertEqual(len([t for t in tags if "python" in t.lower()]), 1)
        self.assertIn("🟢 Junior", tags)

    def test_max_six_tags(self):
        text = "#a #b #c #d #e #f #g удалённо офис гибрид"
        tags = parse_tags(text)
        self.assertLessEqual(len(tags), 6)


class TestParseTitle(unittest.TestCase):
    def test_short_first_line(self):
        text = "Python Backend Developer\nОписание вакансии..."
        title = parse_title(text)
        self.assertEqual(title, "Python Backend Developer")

    def test_pattern_looking_for(self):
        text = "Ищем python разработчика в команду.\nТребования..."
        title = parse_title(text)
        self.assertEqual(title, "python разработчика в команду")

    def test_fallback_long_first_line(self):
        text = "Очень длинная первая строка вакансии, которая явно превышает шестьдесят символов и должна быть обрезана"
        title = parse_title(text)
        self.assertTrue(title.endswith("..."))
        self.assertLessEqual(len(title), 60)


class TestFormatTimeAgo(unittest.TestCase):
    def test_just_now(self):
        now = datetime.now(tz=timezone.utc)
        self.assertEqual(format_time_ago(now), "только что")

    def test_yesterday(self):
        now = datetime.now(tz=timezone.utc)
        yesterday = now - timedelta(days=1)
        result = format_time_ago(yesterday)
        self.assertTrue(result.startswith("вчера в "))

    def test_other_year(self):
        dt = datetime(2023, 6, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = format_time_ago(dt)
        self.assertIn("2023", result)


class TestFormatVacancy(unittest.TestCase):
    def test_empty_text(self):
        result = format_vacancy(None, "channel", "https://t.me/c/1/1", None)
        self.assertIn("Вакансия", result)
        self.assertIn("@channel", result)

    def test_full_card(self):
        text = "Python Developer\nОпыт не нужен. Удалённо. Зарплата 80 000 сом.\n#python #remote"
        date = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        result = format_vacancy(text, "jobs_kg", "https://t.me/jobs_kg/123", date)
        self.assertIn("Python Developer", result)
        self.assertIn("80 000 сом", result)
        self.assertIn("#python", result)
        self.assertIn("@jobs_kg", result)
        self.assertIn("назад", result)

    def test_emoji_only_edge_case(self):
        result = format_vacancy("🔥🔥🔥", "channel", "url", None)
        self.assertIn("🔥🔥🔥", result)


if __name__ == "__main__":
    unittest.main()
