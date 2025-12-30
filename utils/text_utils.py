"""Утилиты для работы с текстом"""

from typing import List, Tuple


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


def _find_split_index(text: str, max_length: int) -> int:
    window = text[: max_length + 1]
    split_idx = max(window.rfind("\n"), window.rfind(" "), window.rfind("\t"))
    return split_idx if split_idx > 0 else max_length


def split_text_once(text: str, max_length: int) -> Tuple[str, str]:
    """Делит текст на две части, первая не превышает max_length."""
    if not text or not text.strip():
        return "", ""

    text = text.strip()
    if len(text) <= max_length:
        return text, ""

    split_idx = _find_split_index(text, max_length)
    head = text[:split_idx].rstrip()
    tail = text[split_idx:].lstrip()
    return head, tail


def split_text(text: str, max_length: int) -> List[str]:
    """Делит текст на части длиной до max_length."""
    if not text or not text.strip():
        return []

    parts = []
    remainder = text.strip()
    while remainder:
        head, remainder = split_text_once(remainder, max_length)
        if not head:
            break
        parts.append(head)
    return parts
