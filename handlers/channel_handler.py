"Обработчик команд и сообщений с каналами"

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
import logging
from typing import Callable, Any, Optional

import aiohttp

from utils.parser import TelegramWebScraper, TelegramWebError, parse_post_link, is_valid_channel_username
from utils.llm_service import rewrite_post
from utils.formatter import format_summary
from utils.text_utils import split_text, split_text_once
from config import MAX_PAGES_PER_REQUEST, MAX_MESSAGE_LENGTH, MAX_CAPTION_LENGTH
from utils.states import PostSelectionState

router = Router()
logger = logging.getLogger(__name__)


async def with_status_message(
    message: Message, status_text: str, action: Callable, *args, **kwargs
) -> Any:
    """Выполняет действие с отображением статусного сообщения"""
    status_msg = await message.answer(status_text)
    try:
        result = await action(*args, **kwargs)
        await status_msg.delete()
        return result
    except Exception as e:
        await status_msg.edit_text(f"❌ {e}")
        raise


async def send_rewritten_post(
    message: Message, post: dict, custom_prompt: Optional[str], model: Optional[str]
):
    """Общая функция для рерайта и отправки поста (с видео, фото или без)"""
    rewritten = await rewrite_post(post, custom_prompt, model)
    photo_url = post.get("photo_url")
    photo_file_id = post.get("photo_file_id")
    video_url = post.get("video_url")
    video_file_id = post.get("video_file_id")

    has_media = bool(video_file_id or video_url or photo_file_id or photo_url)
    caption, remainder = split_text_once(rewritten, MAX_CAPTION_LENGTH)
    extra_text_chunks = split_text(remainder, MAX_MESSAGE_LENGTH) if remainder else []
    text_chunks = split_text(rewritten, MAX_MESSAGE_LENGTH)

    async def send_text_chunks(chunks: list[str]) -> None:
        for chunk in chunks:
            await message.answer(chunk, parse_mode=None)

    # Попытка отправить видео через file_id (из пересланных сообщений)
    if video_file_id:
        try:
            await message.answer_video(
                video=video_file_id, caption=caption, parse_mode=None
            )
            if extra_text_chunks:
                await send_text_chunks(extra_text_chunks)
            return
        except Exception as e:
            logger.error("Failed to send video by file_id: %s", e)

    # Попытка скачать и отправить видео по URL
    if video_url:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                }
                async with session.get(
                    video_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                    ssl=False,  # CDN Telegram использует self-signed сертификат
                ) as resp:
                    if resp.status == 200:
                        # Проверка размера (лимит Telegram: 50 МБ)
                        content_length = resp.headers.get('Content-Length')
                        if content_length and int(content_length) > 50 * 1024 * 1024:
                            logger.warning("Video too large: %s bytes", content_length)
                        else:
                            video_bytes = await resp.read()
                            video_file = BufferedInputFile(video_bytes, filename="video.mp4")
                            await message.answer_video(
                                video=video_file, caption=caption, parse_mode=None
                            )
                            if extra_text_chunks:
                                await send_text_chunks(extra_text_chunks)
                            return
                    else:
                        logger.warning("Failed to download video: HTTP %s", resp.status)
        except Exception as e:
            logger.error("Failed to download/send video: %s", e)

    if photo_file_id:
        try:
            await message.answer_photo(
                photo=photo_file_id, caption=caption, parse_mode=None
            )
            if extra_text_chunks:
                await send_text_chunks(extra_text_chunks)
            return
        except Exception as e:
            logger.error("Failed to send photo by file_id: %s", e)

    if photo_url:
        try:
            # Загружаем фото в память, т.к. Telegram не может загрузить с CDN напрямую
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                }
                async with session.get(
                    photo_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False,  # CDN Telegram использует self-signed сертификат
                ) as resp:
                    if resp.status == 200:
                        photo_bytes = await resp.read()
                        photo_file = BufferedInputFile(photo_bytes, filename="photo.jpg")
                        await message.answer_photo(
                            photo=photo_file, caption=caption, parse_mode=None
                        )
                        if extra_text_chunks:
                            await send_text_chunks(extra_text_chunks)
                        return
                    else:
                        logger.warning("Failed to download photo: HTTP %s", resp.status)
        except Exception as e:
            logger.error("Failed to download/send photo: %s", e)

    # Fallback: отправить только текст
    if not has_media and not text_chunks:
        return
    await send_text_chunks(text_chunks)


@router.message(PostSelectionState.waiting_for_selection)
async def handle_post_selection(message: Message, state: FSMContext):
    """Обработка выбора поста по номеру"""
    text = (message.text or "").strip()
    if not text:
        return
    if not text.isdigit():
        if any(x in text.lower() for x in ["t.me", "@", "http"]) or is_valid_channel_username(text):
            return await handle_channel_link(message, state)
        return await message.answer(
            "❌ Отправь номер поста цифрой или пришли ссылку на канал заново."
        )
    post_number = int(text)
    data = await state.get_data()
    posts = data.get("posts", [])
    custom_prompt = data.get("rewrite_prompt")
    selected_model = data.get("selected_model")

    if not posts:
        await state.clear()
        return await message.answer(
            "❌ Список постов пуст. Отправь ссылку на канал заново."
        )

    if not 1 <= post_number <= len(posts):
        return await message.answer(
            f"❌ Некорректный номер. Выбери от 1 до {len(posts)}"
        )

    selected_post = posts[post_number - 1]

    async def rewrite_action():
        await send_rewritten_post(message, selected_post, custom_prompt, selected_model)
        await state.set_state(PostSelectionState.waiting_for_selection)

    try:
        await with_status_message(
            message, "⏳ Рерайт поста через LLM...", rewrite_action
        )
    except Exception:
        logger.exception("Rewrite error for post %d", post_number)


async def handle_direct_post_link(
    message: Message, state: FSMContext, post_info: tuple[str, int]
):
    """
    Обрабатывает прямую ссылку на пост: загружает один пост и делает рерайт.

    Args:
        message: Message от пользователя
        state: FSM контекст (может содержать кастомный промпт)
        post_info: Кортеж (channel_slug, post_id) из parse_post_link()
    """
    channel_slug, post_id = post_info

    # Получить кастомный промпт и модель из FSM state если они были установлены
    data = await state.get_data()
    custom_prompt = data.get("rewrite_prompt")
    selected_model = data.get("selected_model")

    async def fetch_and_rewrite():
        scraper = TelegramWebScraper()
        post = scraper.fetch_single_post(channel_slug, post_id)
        await send_rewritten_post(message, post, custom_prompt, selected_model)

    try:
        await with_status_message(
            message,
            "⏳ Загрузка и рерайт поста...",
            fetch_and_rewrite
        )
    except TelegramWebError as e:
        logger.error("Direct post fetch error %s/%d: %s", channel_slug, post_id, e)
        # Ошибка уже показана в with_status_message
    except Exception:
        logger.exception("Unexpected error for direct post %s/%d", channel_slug, post_id)
        # Ошибка уже показана в with_status_message


async def handle_channel_scan(message: Message, state: FSMContext, channel: str):
    """
    Сканирует канал и использует FSM для выбора поста пользователем.

    Это существующая логика обработки ссылок на каналы.

    Args:
        message: Message от пользователя
        state: FSM контекст
        channel: Ссылка на канал (в любом формате)
    """
    async def parse_action():
        posts = TelegramWebScraper().fetch_posts(channel, pages=MAX_PAGES_PER_REQUEST)
        await state.update_data(posts=posts)
        await state.set_state(PostSelectionState.waiting_for_selection)
        await message.answer(format_summary(posts))

    try:
        await with_status_message(message, "⏳ Парсинг канала...", parse_action)
    except TelegramWebError as e:
        logger.error("Parsing error for %s: %s", channel, e)
    except Exception:
        logger.exception("Unexpected error for %s", channel)


@router.message(F.forward_from_chat)
async def handle_forwarded_post(message: Message, state: FSMContext):
    """
    Обрабатывает пересланные посты из каналов.
    Извлекает текст и медиа напрямую из сообщения, что позволяет работать
    даже с приватными каналами без использования парсера.
    """
    # Извлекаем текст или подпись к медиа
    text = message.text or message.caption or ""

    if not text or len(text) < 10:
        return await message.answer("❌ Пост слишком короткий для рерайта.")

    # Извлекаем фото, если оно есть
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id

    # Извлекаем видео, если оно есть
    video_file_id = None
    if message.video:
        video_file_id = message.video.file_id

    # Формируем объект поста для пайплайна
    post_data = {
        "text": text,
        "photo_file_id": photo_file_id,
        "video_file_id": video_file_id,
        "post_link": "forwarded_post"
    }

    # Получаем настройки пользователя
    data = await state.get_data()
    custom_prompt = data.get("rewrite_prompt")
    selected_model = data.get("selected_model")

    async def rewrite_action():
        await send_rewritten_post(message, post_data, custom_prompt, selected_model)

    try:
        await with_status_message(
            message, "⏳ Рерайт пересланного поста...", rewrite_action
        )
    except Exception:
        logger.exception("Forwarded post rewrite error")


@router.message(F.text)
async def handle_channel_link(message: Message, state: FSMContext):
    """
    Роутер для обработки ссылок на каналы и прямых ссылок на посты.

    Определяет тип ссылки и делегирует обработку:
    - Прямая ссылка на пост (t.me/channel/123) -> handle_direct_post_link()
    - Ссылка на канал (t.me/channel) -> handle_channel_scan()
    """
    if not message.text:
        return
    channel = message.text.strip()

    # Валидация входа: проверяем что это похоже на ссылку на Telegram
    if not any(x in channel.lower() for x in ["t.me", "@", "http"]):
        if "/" not in channel and len(channel) > 3:
            # Проверяем формат имени канала (только латиница, цифры, подчеркивание, 5-32 символа)
            if not is_valid_channel_username(channel):
                return await message.answer(
                    "❌ Некорректное имя канала\n\n"
                    "Имя канала должно:\n"
                    "• Содержать только латинские буквы, цифры и подчеркивание\n"
                    "• Быть длиной от 5 до 32 символов\n"
                    "• Не начинаться с цифры\n\n"
                    "Или отправьте полную ссылку на канал (например, https://t.me/channelname)"
                )
            channel = f"@{channel}"
        else:
            return await message.answer("❌ Некорректная ссылка на канал")

    # Определяем тип ссылки: прямая на пост или на канал?
    post_info = parse_post_link(channel)

    if post_info:
        # Это прямая ссылка на пост (например, t.me/channel/345)
        await handle_direct_post_link(message, state, post_info)
    else:
        # Это ссылка на канал (например, t.me/channel)
        await handle_channel_scan(message, state, channel)
