"""
Standalone модуль для парсинга Telegram каналов через веб t.me/s/

Примеры использования:
    from parser import TelegramWebScraper

    scraper = TelegramWebScraper()

    # Спарсить 1 страницу канала
    posts = scraper.fetch_posts("@channelname")

    # Спарсить 3 страницы канала
    posts = scraper.fetch_posts("https://t.me/channelname", pages=3)

    # Обработать результаты
    for post in posts:
        print(f"Пост: {post['post_link']}")
        print(f"Текст: {post['text'][:100]}...")
        print(f"Просмотры: {post['views']}, Пересылки: {post['forwards']}")
        print(f"Дата: {post['posted_at']}")
        print(f"Медиа: {'Да' if post['has_media'] else 'Нет'}")
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

logger = logging.getLogger(__name__)

# Максимум страниц за один запрос
MAX_PAGES = 20


class TelegramWebError(Exception):
    """Базовая ошибка при работе с веб-версией Telegram."""


def _normalize_channel(channel: str) -> str:
    """
    Нормализует название канала из различных форматов.

    Примеры входных данных:
        - "https://t.me/channelname"
        - "https://t.me/s/channelname"
        - "http://t.me/channelname"
        - "t.me/channelname"
        - "@channelname"
        - "channelname"
        - "channelname/123"  # с ID поста

    Результат всегда: "channelname"

    Args:
        channel: Ссылка на канал в любом формате

    Returns:
        Нормализованное название канала (без @ и домена)
    """
    cleaned = channel.strip()
    cleaned = re.sub(r"^https?://t\.me/(s/)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.lstrip("@")
    return cleaned.split("/")[0]


def normalize_channel_link(channel: str) -> str:
    """
    Возвращает каноническую ссылку на канал.

    Args:
        channel: Ссылка на канал в любом формате

    Returns:
        Каноническая ссылка (https://t.me/channelname)
    """
    slug = _normalize_channel(channel)
    return f"https://t.me/{slug}"


def parse_post_link(url: str) -> Optional[tuple[str, int]]:
    """
    Проверяет, является ли URL прямой ссылкой на пост, и извлекает канал и ID.

    Примеры:
        - "https://t.me/prog_ai/345" -> ("prog_ai", 345)
        - "https://t.me/s/prog_ai/345" -> ("prog_ai", 345)
        - "t.me/prog_ai/345" -> ("prog_ai", 345)
        - "https://t.me/prog_ai" -> None (нет ID)
        - "@prog_ai" -> None (нет ID)
        - "@prog_ai/345" -> ("prog_ai", 345)

    Args:
        url: Ссылка на пост или канал в любом формате

    Returns:
        Кортеж (channel_slug, post_id) если прямая ссылка, иначе None
    """
    cleaned = url.strip()

    # Удаляем протокол и домен (https?://t.me/)
    cleaned = re.sub(r"^https?://t\.me/(s/)?", "", cleaned, flags=re.IGNORECASE)

    # Если нет https://, пробуем удалить t.me/ в начале
    if cleaned == url.strip():
        cleaned = re.sub(r"^t\.me/(s/)?", "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.lstrip("@")

    # Разделяем по "/"
    parts = cleaned.split("/")

    # Для прямой ссылки нужно ровно 2 части: канал и ID
    if len(parts) != 2:
        return None

    channel_slug, post_id_str = parts

    # Проверяем что канал не пуст
    if not channel_slug:
        return None

    # Проверяем что ID — число
    if not post_id_str.isdigit():
        return None

    try:
        post_id = int(post_id_str)
        # ID должен быть положительным числом
        if post_id <= 0:
            return None
        return (channel_slug, post_id)
    except ValueError:
        return None


def _parse_counter(raw: str) -> int:
    """
    Парсит числовые счетчики с суффиксами K (тысячи) и M (миллионы).

    Примеры:
        - "1 234" → 1234
        - "1.2K" → 1200
        - "3,5M" → 3500000
        - "5K" → 5000

    Args:
        raw: Строка со счетчиком

    Returns:
        Целое число
    """
    text = raw.replace(" ", "").upper()
    match = re.match(r"([0-9]+(?:[\.,][0-9]+)?)([KM]?)", text)
    if not match:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits.isdigit() else 0

    number_part, suffix = match.groups()
    number = float(number_part.replace(",", "."))

    if suffix == "K":
        number *= 1_000
    elif suffix == "M":
        number *= 1_000_000

    return int(number)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Парсит ISO datetime из атрибута <time datetime="...">

    Args:
        value: ISO строка с датой и временем

    Returns:
        datetime объект в UTC или None если парсинг не удался
    """
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def _extract_photo_url(message: Tag) -> Optional[str]:
    """Извлекает прямую ссылку на фото из поста."""
    # 1. Проверяем элементы с потенциальными фото
    selectors = [
        ".tgme_widget_message_photo_wrap",
        ".tgme_widget_message_photo",
        ".tgme_widget_message_video_thumb",
        ".tgme_widget_message_video_player"
    ]
    
    for selector in selectors:
        for el in message.select(selector):
            style = el.get("style", "")
            if style:
                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                if match:
                    url = match.group(1)
                    if url.startswith("//"):
                        url = "https:" + url
                    return url
            
            # Если это тег img
            if el.name == "img" and el.has_attr("src"):
                url = el["src"]
                if url.startswith("//"):
                    url = "https:" + url
                return url

    # 2. Поиск любого background-image в элементах со стилем
    for el in message.find_all(style=True):
        style = el["style"]
        if "background-image" in style:
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if match:
                url = match.group(1)
                if url.startswith("//"):
                    url = "https:" + url
                return url
                
    # 3. Поиск тегов img (кроме аватаров)
    for img in message.find_all("img"):
        classes = img.get("class", [])
        if isinstance(classes, str):
            classes = [classes]
        if "tgme_widget_message_user_photo" not in classes:
            url = img.get("src")
            if url:
                if url.startswith("//"):
                    url = "https:" + url
                return url

    return None


def _extract_video_url(message: Tag) -> Optional[str]:
    """Извлекает прямую ссылку на видео из поста."""
    # 1. Проверяем элементы с потенциальными видео
    selectors = [
        ".tgme_widget_message_video",
        ".tgme_widget_message_video_player",
        ".tgme_widget_message_video_wrap"
    ]

    for selector in selectors:
        for el in message.select(selector):
            # Проверяем background-image в стиле
            style = el.get("style", "")
            if style and "background-image" in style:
                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                if match:
                    url = match.group(1)
                    if url.startswith("//"):
                        url = "https:" + url
                    return url

            # Ищем <video> теги внутри элемента
            video_tag = el.find("video")
            if video_tag:
                # Проверяем src атрибут тега video
                if video_tag.has_attr("src"):
                    url = video_tag["src"]
                    if url.startswith("//"):
                        url = "https:" + url
                    return url

                # Проверяем <source> элементы внутри <video>
                source = video_tag.find("source")
                if source and source.has_attr("src"):
                    url = source["src"]
                    if url.startswith("//"):
                        url = "https:" + url
                    return url

    # 2. Поиск <video> тегов в сообщении
    for video in message.find_all("video"):
        if video.has_attr("src"):
            url = video["src"]
            if url.startswith("//"):
                url = "https:" + url
            return url

        # Проверяем <source> элементы
        source = video.find("source")
        if source and source.has_attr("src"):
            url = source["src"]
            if url.startswith("//"):
                url = "https:" + url
            return url

    # 3. Поиск data-src атрибутов (для ленивой загрузки)
    for el in message.find_all(attrs={"data-src": True}):
        url = el.get("data-src")
        if url:
            if url.startswith("//"):
                url = "https:" + url
            return url

    return None


def _extract_text(message) -> str:
    """Извлекает текст сообщения из HTML."""
    block = message.select_one(".tgme_widget_message_text")
    return block.get_text("\n", strip=True) if block else ""


def _extract_post_link(message) -> Optional[str]:
    """Извлекает ссылку на пост из HTML."""
    link = message.select_one("a.tgme_widget_message_date")
    if link and link.has_attr("href"):
        return link["href"]
    return None


def _extract_views(message) -> int:
    """Извлекает количество просмотров из HTML."""
    views_tag = message.select_one(".tgme_widget_message_views")
    return _parse_counter(views_tag.get_text(strip=True)) if views_tag else 0


def _extract_forwards(message) -> int:
    """Извлекает количество пересылок из HTML."""
    forwards_tag = message.select_one(".tgme_widget_message_forwards")
    return _parse_counter(forwards_tag.get_text(strip=True)) if forwards_tag else 0


def _detect_media_type(message) -> dict:
    """
    Определяет детальный тип медиа в сообщении.

    Returns:
        dict: {
            'type': 'text'|'photo'|'video'|'gallery'|'poll'|'voice'|'document',
            'has_text': bool,
            'media_count': int
        }
    """
    has_text = bool(message.select_one(".tgme_widget_message_text"))

    # Опрос
    if message.select_one(".tgme_widget_message_poll"):
        return {"type": "poll", "has_text": has_text, "media_count": 1}

    # Голосовое
    if message.select_one(".tgme_widget_message_voice"):
        return {"type": "voice", "has_text": has_text, "media_count": 1}

    # Документ
    if message.select_one(".tgme_widget_message_document"):
        return {"type": "document", "has_text": has_text, "media_count": 1}

    # Видео
    if message.select_one(".tgme_widget_message_video"):
        return {"type": "video", "has_text": has_text, "media_count": 1}

    # Фото/галерея
    photos = message.select(".tgme_widget_message_photo_wrap")
    if photos and len(photos) > 1:
        return {"type": "gallery", "has_text": has_text, "media_count": len(photos)}
    elif message.select_one(".tgme_widget_message_photo"):
        return {"type": "photo", "has_text": has_text, "media_count": 1}

    # Только текст
    return {"type": "text", "has_text": has_text, "media_count": 0}


def _detect_media(message) -> bool:
    """Определяет наличие медиа в сообщении (фото, видео, документ, голос и т.д.)."""
    result = _detect_media_type(message)
    return result["type"] != "text"


def _extract_message_id(message) -> Optional[int]:
    """Извлекает ID сообщения из HTML для пагинации."""
    post_attr = message.get("data-post") if isinstance(message, Tag) else None
    if not post_attr:
        return None

    try:
        return int(str(post_attr).split("/")[-1])
    except (TypeError, ValueError):
        return None


def _is_forwarded(message) -> bool:
    """Проверяет является ли сообщение пересланным (игнорируются)."""
    if not isinstance(message, Tag):
        return False
    # Присутствует блок forwarded-from
    if message.select_one(".tgme_widget_message_forwarded_from"):
        return True
    # Иногда forward-плашка имеет другие классы
    if message.select_one(".tgme_widget_message_forwarded_post_author"):
        return True
    return False


class TelegramWebScraper:
    """
    Парсер Telegram каналов через веб t.me/s/

    Поддерживает парсинг публичных каналов через веб-интерфейс.
    Не требует Bot API токена, работает через простые HTTP запросы.

    Пример:
        scraper = TelegramWebScraper()
        posts = scraper.fetch_posts("@mychannel", pages=3)
        for post in posts:
            print(f"Текст: {post['text']}")
            print(f"Просмотры: {post['views']}")
    """

    BASE_URL = "https://t.me/s"

    def __init__(self, session: Optional[requests.Session] = None):
        """
        Инициализирует парсер.

        Args:
            session: Опциональная requests.Session для переиспользования соединения
        """
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch_posts(self, channel: str, pages: int = 1) -> List[dict]:
        """
        Спарсить посты из канала с пагинацией.

        Args:
            channel: Ссылка на канал (@channel, https://t.me/channel и т.д.)
            pages: Количество страниц для парсинга (по умолчанию 1, макс 20)

        Returns:
            Список словарей с информацией о постах:
            [
                {
                    'channel_slug': 'channelname',
                    'channel_link': 'https://t.me/channelname',
                    'post_link': 'https://t.me/channelname/123',
                    'text': 'Текст поста...',
                    'posted_at': datetime(2024, 12, 29, 10, 30, 0),
                    'views': 1200,
                    'forwards': 45,
                    'has_media': True
                },
                ...
            ]

        Raises:
            TelegramWebError: Если канал не найден, приватный, требуется авторизация
                или при ошибке парсинга HTML
        """
        slug = _normalize_channel(channel)
        if not slug:
            raise TelegramWebError("Некорректное имя канала")

        pages = max(1, min(pages, MAX_PAGES))  # защита от слишком глубокой пагинации

        all_posts: list[dict] = []
        next_before: Optional[int] = None

        for _ in range(pages):
            page_posts, next_before = self._fetch_page(slug, next_before)
            if not page_posts:
                break
            all_posts.extend(page_posts)

            if not next_before:
                break

        if not all_posts:
            raise TelegramWebError(
                "Не удалось распарсить посты (возможно, Telegram изменил верстку)"
            )

        # Сортировка по message_id (новые сверху), без хранения служебного поля
        ordered = sorted(
            all_posts, key=lambda p: p.get("message_id") or 0, reverse=True
        )
        for p in ordered:
            p.pop("message_id", None)

        return ordered

    def _fetch_page(
        self, slug: str, before: Optional[int]
    ) -> tuple[list[dict], Optional[int]]:
        """
        Спарсить одну страницу канала.

        Args:
            slug: Нормализованное имя канала
            before: ID сообщения для пагинации (для получения старых постов)

        Returns:
            Кортеж (список постов на странице, ID для следующей страницы или None)
        """
        url = f"{self.BASE_URL}/{slug}"
        if before:
            url = f"{url}?before={before}"

        try:
            response = self.session.get(url, timeout=15)
        except requests.RequestException as exc:
            raise TelegramWebError(f"Ошибка запроса: {exc}") from exc

        if response.status_code == 404:
            raise TelegramWebError("Канал не найден или приватный")
        if response.status_code in (403, 429):
            raise TelegramWebError(
                f"Доступ к t.me запрещен (HTTP {response.status_code}), требуется прокси/капча"
            )
        if response.status_code != 200:
            raise TelegramWebError(f"t.me вернул статус {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        if soup.select_one(".tgme_page_error"):
            raise TelegramWebError(
                "Telegram вернул страницу ошибки (возможно нужна авторизация или канал скрыт)"
            )

        messages = soup.select(".tgme_widget_message")
        if not messages:
            return [], None

        posts: list[dict] = []
        msg_ids: list[int] = []

        for message in reversed(messages):  # новейшие первыми внутри страницы
            post_link = _extract_post_link(message)
            if not post_link:
                continue

            # Включаем forwarded посты
            # if _is_forwarded(message):
            #     continue

            msg_id = _extract_message_id(message)
            if msg_id:
                msg_ids.append(msg_id)

            posted_at = None
            time_tag = message.find("time")
            if isinstance(time_tag, Tag) and time_tag.has_attr("datetime"):
                datetime_attr = time_tag.get("datetime")
                posted_at = _parse_datetime(
                    datetime_attr if isinstance(datetime_attr, str) else None
                )

            posts.append(
                {
                    "channel_slug": slug,
                    "channel_link": f"https://t.me/{slug}",
                    "post_link": post_link,
                    "text": _extract_text(message),
                    "posted_at": posted_at,
                    "views": _extract_views(message),
                    "forwards": _extract_forwards(message),
                    "has_media": _detect_media(message),
                    "is_forwarded": _is_forwarded(message),
                    "media_type": _detect_media_type(message),
                    "photo_url": _extract_photo_url(message),
                    "video_url": _extract_video_url(message),
                    "message_id": msg_id,
                }
            )

        next_before = None
        if msg_ids:
            min_id = min(msg_ids)
            next_before = min_id if min_id > 1 else None

        return posts, next_before

    def fetch_single_post(self, channel: str, post_id: int) -> dict:
        """
        Загружает один конкретный пост по его ID из публичного канала.

        Args:
            channel: Название канала (в любом формате, будет нормализовано)
            post_id: ID поста (положительное целое число)

        Returns:
            Словарь с информацией о посте:
            {
                'channel_slug': 'channelname',
                'channel_link': 'https://t.me/channelname',
                'post_link': 'https://t.me/channelname/123',
                'text': 'Текст поста...',
                'posted_at': datetime(...),
                'views': 1200,
                'forwards': 45,
                'has_media': True,
                'is_forwarded': False,
                'media_type': {...}
            }

        Raises:
            TelegramWebError: Если пост не найден (404), канал приватный (403),
                             запрос заблокирован (429), или при ошибке парсинга
        """
        slug = _normalize_channel(channel)
        if not slug:
            raise TelegramWebError("Некорректное имя канала")

        # URL для прямого доступа к посту: https://t.me/s/channelname/postid
        url = f"{self.BASE_URL}/{slug}/{post_id}"

        try:
            response = self.session.get(url, timeout=15)
        except requests.RequestException as exc:
            raise TelegramWebError(f"Ошибка запроса: {exc}") from exc

        # Обработка HTTP ошибок
        if response.status_code == 404:
            raise TelegramWebError(
                "Пост не найден. Возможно, он был удален или канал приватный."
            )
        if response.status_code in (403, 429):
            raise TelegramWebError(
                f"Доступ к t.me запрещен (HTTP {response.status_code})"
            )
        if response.status_code != 200:
            raise TelegramWebError(f"t.me вернул статус {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Проверяем на страницу ошибки
        if soup.select_one(".tgme_page_error"):
            raise TelegramWebError(
                "Пост недоступен (возможно, канал приватный или пост удален)"
            )

        # Ищем сообщение с конкретным ID на странице
        # Используем data-post атрибут для точного поиска нужного поста
        message = soup.select_one(f'.tgme_widget_message[data-post="{slug}/{post_id}"]')
        if not message:
            raise TelegramWebError(
                "Пост не найден на странице. Возможно, он был удален или ID неверный."
            )

        # Извлекаем ссылку на пост
        post_link = _extract_post_link(message)
        if not post_link:
            raise TelegramWebError("Не удалось извлечь ссылку на пост")

        # Извлекаем datetime
        posted_at = None
        time_tag = message.find("time")
        if isinstance(time_tag, Tag) and time_tag.has_attr("datetime"):
            datetime_attr = time_tag.get("datetime")
            posted_at = _parse_datetime(
                datetime_attr if isinstance(datetime_attr, str) else None
            )

        return {
            "channel_slug": slug,
            "channel_link": f"https://t.me/{slug}",
            "post_link": post_link,
            "text": _extract_text(message),
            "posted_at": posted_at,
            "views": _extract_views(message),
            "forwards": _extract_forwards(message),
            "has_media": _detect_media(message),
            "is_forwarded": _is_forwarded(message),
            "media_type": _detect_media_type(message),
            "photo_url": _extract_photo_url(message),
            "video_url": _extract_video_url(message),
        }
