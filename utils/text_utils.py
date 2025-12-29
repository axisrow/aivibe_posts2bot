"""Утилиты для работы с текстом"""


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезает текст до указанной длины с добавлением '...'"""
    return (
        ""
        if not (text := (text or "").strip())
        else (
            text
            if len(text) <= max_length
            else text[:max_length].rsplit(" ", 1)[0] + "..."
        )
    )
