"""Форматирование сводки постов для Telegram"""

from typing import List

from config import MAX_MESSAGE_LENGTH, MAX_POSTS_IN_SUMMARY

from .post_types import get_post_emoji
from .text_utils import truncate_text


def format_summary(posts: List[dict]) -> str:
    """Форматирует сводку постов в одно Telegram сообщение"""
    if not posts:
        return "❌ Посты не найдены"

    posts = posts[:MAX_POSTS_IN_SUMMARY]

    header = [
        f"📊 <b>Сводка канала</b> ({len(posts)} постов)\n",
        f"💡 <i>Отправь номер поста (1-{len(posts)}) для рерайта</i>\n",
        "=" * 40,
    ]

    post_lines = []
    for i, p in enumerate(posts, 1):
        parts = [f"\n{get_post_emoji(p)} <b>Пост #{i}</b>"]
        
        if link := p.get("post_link"):
            parts.append(f'🔗 <a href="{link}">Открыть</a>')
            
        views = p.get("views", 0)
        forwards = p.get("forwards", 0)
        parts.append(f"👁 {views:,} | 📤 {forwards:,}")
        
        if p.get("is_forwarded"):
            parts.append("↪️ <i>Forwarded</i>")
            
        if text := p.get("text"):
            parts.append(f"📝 {truncate_text(text, 200)}")
            
        parts.append("-" * 40)
        post_lines.append("\n".join(parts))

    result = "\n".join(header + post_lines)

    return (
        result[: MAX_MESSAGE_LENGTH - 100]
        + "\n\n⚠️ Сообщение обрезано (слишком много постов)"
        if len(result) > MAX_MESSAGE_LENGTH
        else result
    )
