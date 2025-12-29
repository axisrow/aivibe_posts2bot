"""Тесты для форматирования сводки постов"""

from datetime import datetime
from utils.formatter import format_summary


def test_format_summary_empty():
    """Тест форматирования пустого списка постов"""
    result = format_summary([])
    assert result == "❌ Посты не найдены"


def test_format_summary_single_post():
    """Тест форматирования одного поста"""
    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/1",
            "text": "Тестовый пост",
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        }
    ]

    result = format_summary(posts)

    assert "1 постов" in result
    assert "Тестовый пост" in result
    assert "1,000" in result
    assert "test_channel/1" in result


def test_format_summary_multiple_posts():
    """Тест форматирования нескольких постов"""
    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/1",
            "text": "Первый пост",
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        },
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/2",
            "text": "Второй пост",
            "posted_at": datetime(2024, 1, 2, 12, 0, 0),
            "views": 2000,
            "forwards": 100,
            "media_type": {"type": "photo", "has_text": True, "media_count": 1},
        },
    ]

    result = format_summary(posts)

    assert "2 постов" in result
    assert "Первый пост" in result
    assert "Второй пост" in result
    assert "test_channel/1" in result
    assert "test_channel/2" in result


def test_format_summary_with_emoji():
    """Тест что форматирование включает эмодзи"""
    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/1",
            "text": "Тестовый пост",
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        }
    ]

    result = format_summary(posts)

    # Проверяем наличие эмодзи
    assert "📊" in result  # Заголовок сводки
    assert "💡" in result  # Совет
    assert "🔗" in result  # Ссылка
    assert "👁" in result  # Просмотры


def test_format_summary_truncates_long_text():
    """Тест что длинный текст обрезается"""
    long_text = "А" * 300  # Текст длиннее лимита truncate_text (200)

    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/1",
            "text": long_text,
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        }
    ]

    result = format_summary(posts)

    # Проверяем что полный текст не в результате
    assert long_text not in result
    # Проверяем что результат был сгенерирован
    assert "А" in result


def test_format_summary_respects_max_posts():
    """Тест что форматирование ограничивает количество постов"""
    from config import MAX_POSTS_IN_SUMMARY

    # Создаем больше постов чем лимит
    posts = []
    for i in range(MAX_POSTS_IN_SUMMARY + 5):
        posts.append(
            {
                "channel_slug": "test_channel",
                "post_link": f"https://t.me/test_channel/{i + 1}",
                "text": f"Пост {i + 1}",
                "posted_at": datetime(2024, 1, 1, 12, 0, 0),
                "views": 1000,
                "forwards": 50,
                "media_type": {"type": "text", "has_text": True, "media_count": 0},
            }
        )

    result = format_summary(posts)

    # Проверяем что показано только MAX_POSTS_IN_SUMMARY постов
    assert f"{MAX_POSTS_IN_SUMMARY} постов" in result
    # Последний пост должен быть в результате
    assert f"Пост {MAX_POSTS_IN_SUMMARY}" in result
    # Лишний пост не должен быть в результате
    assert f"Пост {MAX_POSTS_IN_SUMMARY + 1}" not in result


def test_format_summary_with_no_link():
    """Тест форматирования поста без ссылки"""
    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": None,
            "text": "Пост без ссылки",
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        }
    ]

    result = format_summary(posts)

    assert "Пост без ссылки" in result
    # Ссылка не должна быть
    assert "🔗" not in result or "test_channel" not in result


def test_format_summary_has_header_and_footer():
    """Тест что сводка содержит заголовок и инструкции"""
    posts = [
        {
            "channel_slug": "test_channel",
            "post_link": "https://t.me/test_channel/1",
            "text": "Тест",
            "posted_at": datetime(2024, 1, 1, 12, 0, 0),
            "views": 1000,
            "forwards": 50,
            "media_type": {"type": "text", "has_text": True, "media_count": 0},
        }
    ]

    result = format_summary(posts)

    # Проверяем наличие заголовка
    assert "Сводка канала" in result
    # Проверяем наличие инструкции
    assert "номер поста" in result or "для рерайта" in result
