"""Определение типов постов и соответствующих эмодзи"""

# Маппинг типов медиа на эмодзи
EMOJI_MAP = {
    "poll": "📊",
    "voice": "🎤",
    "document": "📎",
    "video": {"with_text": "🎬", "default": "📹"},
    "gallery": {"with_text": "🖼📸", "default": "🖼"},
    "photo": {"with_text": "🖼✍️", "default": "🖼"},
}


def get_post_emoji(post: dict) -> str:
    """Определяет эмодзи для типа поста"""
    # Старый формат (has_media)
    if not (media_type := post.get("media_type")):
        return "🖼" if post.get("has_media") else "📄"

    post_type = media_type.get("type", "text")
    emoji_obj = EMOJI_MAP.get(post_type, "📝")

    # Для типов с вариантами по has_text
    if isinstance(emoji_obj, dict):
        return emoji_obj.get(
            "with_text" if media_type.get("has_text") else "default", "📝"
        )
    return emoji_obj if isinstance(emoji_obj, str) else "📝"
