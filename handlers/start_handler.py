"""Обработчик базовых команд (start, help, settings)"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
import logging
from pathlib import Path

from config import (
    DEFAULT_REWRITE_PROMPT,
    OLLAMA_MODEL,
    AVAILABLE_MODELS,
)

router = Router()
logger = logging.getLogger(__name__)

INSTRUCTION_IMAGE_PATH = Path(__file__).resolve().parents[1] / "images" / "instruction.png"

HELP_TEXT = {
    "start": (
        "👋 Этот бот рерайтит посты из Telegram каналов.\n\n"
        "<b>Как это работает:</b>\n"
        "1. Пришлите ссылку на канал — получите список постов для выбора\n\n"

        "1. Или пришлите ссылку на пост или просто перешлите пост в бот\n"
        "3. Получите готовый рерайт для вашего канала\n"
        "4. Отредактируйте пост после публикации при необходимости\n\n"
        
        "⚙️ /settings — настроить промпт и модель\n"
        "❓ /help — список команд"
    ),
    "help": (
        "📖 <b>Команды</b>\n\n"
        "/start — начало работы\n"
        "/settings — текущие настройки\n"
        "/prompt &lt;текст&gt; — установить промпт\n"
        "/model — выбрать модель LLM\n"
        "/help — эта справка\n\n"
        "<b>Способы отправки:</b>\n"
        "• Перешлите пост из канала\n"
        "• Ссылка на пост: t.me/channel/123\n"
        "• Ссылка на канал: @channel или t.me/channel\n\n"
        "При ссылке на канал — выберите номер поста из списка."
    ),
}


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await message.answer(HELP_TEXT["start"])
    await cmd_model(message, state)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    if not INSTRUCTION_IMAGE_PATH.exists():
        logger.warning("Instruction image not found: %s", INSTRUCTION_IMAGE_PATH)
        return await message.answer(HELP_TEXT["help"])

    await message.answer_photo(
        photo=FSInputFile(str(INSTRUCTION_IMAGE_PATH)),
        caption=HELP_TEXT["help"],
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Отображение текущих настроек пользователя"""
    data = await state.get_data()
    custom_prompt = data.get("rewrite_prompt", DEFAULT_REWRITE_PROMPT)
    selected_model = data.get("selected_model", OLLAMA_MODEL)

    text = (
        "⚙️ <b>Ваши настройки:</b>\n\n"
        f"🤖 <b>Модель:</b> <code>{selected_model}</code>\n"
        f"📝 <b>Промпт:</b> <i>{custom_prompt}</i>\n\n"
        "Для изменения:\n"
        "• /prompt &lt;текст&gt;\n"
        "• /model"
    )
    await message.answer(text)


@router.message(Command("model"))
async def cmd_model(message: Message, state: FSMContext):
    """Выбор модели LLM через inline-клавиатуру"""
    data = await state.get_data()
    current_model = data.get("selected_model", OLLAMA_MODEL)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'' if model == current_model else ''}{model}",
            callback_data=f"model:{model}"
        )]
        for model in AVAILABLE_MODELS
    ])

    await message.answer("🤖 <b>Выберите модель:</b>", reply_markup=keyboard)


@router.callback_query(F.data.startswith("model:"))
async def callback_select_model(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора модели через inline-кнопку"""
    model = callback.data.split(":", 1)[1]

    if model not in AVAILABLE_MODELS:
        return await callback.answer("❌ Недопустимая модель", show_alert=True)

    await state.update_data(selected_model=model)
    await callback.message.edit_text(f"✅ Модель установлена: <code>{model}</code>")
    await callback.answer()


@router.message(Command("prompt"))
async def cmd_prompt(message: Message, state: FSMContext):
    """Установка пользовательского промпта для рерайта"""
    if not message.text or len(args := message.text.split(maxsplit=1)) < 2:
        return await message.answer(
            "❌ Укажи промпт после команды:\n/prompt Сделай пост более эмоциональным"
        )

    if not (custom_prompt := args[1].strip()) or len(custom_prompt) < 5:
        return await message.answer("❌ Промпт слишком короткий (минимум 5 символов)")

    await state.update_data(rewrite_prompt=custom_prompt)
    await message.answer(
        f"✅ Промпт установлен:\n\n<i>{custom_prompt}</i>\n\n"
        "Теперь отправь ссылку на канал и выбери пост для рерайта."
    )
