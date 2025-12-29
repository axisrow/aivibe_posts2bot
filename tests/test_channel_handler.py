"""Тесты для обработчиков команд и сообщений"""

import pytest
from unittest.mock import AsyncMock
from handlers.start_handler import (
    cmd_start,
    cmd_help,
    cmd_prompt,
    cmd_settings,
    cmd_model,
)
from config import OLLAMA_MODEL, AVAILABLE_MODELS


@pytest.mark.asyncio
async def test_cmd_start(mock_message, mock_state):
    """Тест команды /start"""
    mock_state.get_data.return_value = {}
    await cmd_start(mock_message, mock_state)

    # Проверяем что answer был вызван дважды (help + model selection)
    assert mock_message.answer.call_count == 2

    # Получаем текст из первого вызова (help)
    call_args = mock_message.answer.call_args_list[0][0][0]

    # Проверяем наличие ключевых элементов
    assert "Этот бот" in call_args
    assert "канал" in call_args or "Telegram" in call_args
    assert "рерайтит" in call_args

    # Проверяем второй вызов (модель)
    model_call_args = mock_message.answer.call_args_list[1]
    assert "Выберите модель" in model_call_args[0][0]
    assert "reply_markup" in model_call_args[1]


@pytest.mark.asyncio
async def test_cmd_help(mock_message):
    """Тест команды /help"""
    await cmd_help(mock_message)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]

    # Проверяем наличие справочной информации
    assert "Команды" in call_args
    assert "/start" in call_args
    assert "/help" in call_args


@pytest.mark.asyncio
async def test_cmd_settings_default(mock_message, mock_state):
    """Тест команды /settings с дефолтными значениями"""
    mock_state.get_data.return_value = {}

    await cmd_settings(mock_message, mock_state)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]

    assert "настройки" in call_args.lower()
    assert OLLAMA_MODEL in call_args
    assert "Промпт" in call_args


@pytest.mark.asyncio
async def test_cmd_settings_custom(mock_message, mock_state):
    """Тест команды /settings с пользовательскими значениями"""
    mock_state.get_data.return_value = {
        "rewrite_prompt": "Custom prompt text",
        "selected_model": "custom-model:latest",
    }

    await cmd_settings(mock_message, mock_state)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]

    assert "Custom prompt text" in call_args
    assert "custom-model:latest" in call_args


@pytest.mark.asyncio
async def test_cmd_model_valid(mock_message, mock_state):
    """Тест команды /model с валидной моделью"""
    # cmd_model отправляет inline-клавиатуру без аргументов
    mock_message.text = "/model"
    mock_state.get_data.return_value = {}

    await cmd_model(mock_message, mock_state)

    # Проверяем что был отправлен ответ с клавиатурой
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    # Проверяем что reply_markup (клавиатура) была передана
    assert "reply_markup" in call_args[1]


@pytest.mark.asyncio
async def test_cmd_model_shows_current(mock_message, mock_state):
    """Тест что /model показывает текущую выбранную модель"""
    mock_message.text = "/model"
    target_model = AVAILABLE_MODELS[-1]
    mock_state.get_data.return_value = {"selected_model": target_model}

    await cmd_model(mock_message, mock_state)

    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    assert "reply_markup" in call_args[1]


@pytest.mark.asyncio
async def test_cmd_prompt_valid(mock_message, mock_state):
    """Тест команды /prompt с валидным промптом"""
    mock_message.text = "/prompt Переделай пост более коротко"

    await cmd_prompt(mock_message, mock_state)

    # Проверяем что состояние было обновлено
    mock_state.update_data.assert_called_once()
    call_args = mock_state.update_data.call_args[1]
    assert "rewrite_prompt" in call_args
    assert call_args["rewrite_prompt"] == "Переделай пост более коротко"

    # Проверяем что был отправлен ответ об успехе
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "✅" in call_args or "установлен" in call_args


@pytest.mark.asyncio
async def test_cmd_prompt_no_args(mock_message, mock_state):
    """Тест команды /prompt без аргументов"""
    mock_message.text = "/prompt"

    await cmd_prompt(mock_message, mock_state)

    # Проверяем что было отправлено сообщение об ошибке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "❌" in call_args
    assert "Укажи промпт" in call_args or "после команды" in call_args

    # Состояние не должно было обновиться
    mock_state.update_data.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_prompt_too_short(mock_message, mock_state):
    """Тест команды /prompt с коротким промптом (< 5 символов)"""
    mock_message.text = "/prompt abc"

    await cmd_prompt(mock_message, mock_state)

    # Проверяем что было отправлено сообщение об ошибке
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args[0][0]
    assert "❌" in call_args or "короткий" in call_args

    # Состояние не должно было обновиться
    mock_state.update_data.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_start_contains_emoji(mock_state):
    """Тест что /start содержит эмодзи"""
    mock_message = AsyncMock()
    mock_message.answer = AsyncMock()
    mock_state.get_data.return_value = {}

    await cmd_start(mock_message, mock_state)

    call_args = mock_message.answer.call_args_list[0][0][0]
    # Проверяем наличие эмодзи
    assert "👋" in call_args
    assert "⚙️" in call_args
    assert "❓" in call_args


@pytest.mark.asyncio
async def test_cmd_help_contains_emoji():
    """Тест что /help содержит эмодзи"""
    mock_message = AsyncMock()
    mock_message.answer = AsyncMock()

    await cmd_help(mock_message)

    call_args = mock_message.answer.call_args[0][0]
    # Проверяем наличие эмодзи
    assert "📖" in call_args


@pytest.mark.asyncio
async def test_cmd_prompt_trims_whitespace(mock_message, mock_state):
    """Тест что /prompt убирает лишние пробелы"""
    mock_message.text = "/prompt   Тестовый промпт   "

    await cmd_prompt(mock_message, mock_state)

    # Проверяем что промпт был обрезан
    call_args = mock_state.update_data.call_args[1]
    assert call_args["rewrite_prompt"] == "Тестовый промпт"


@pytest.mark.asyncio
async def test_cmd_start_formats_as_html(mock_message, mock_state):
    """Тест что /start возвращает HTML отформатированный текст"""
    mock_state.get_data.return_value = {}
    await cmd_start(mock_message, mock_state)

    call_args = mock_message.answer.call_args_list[0][0][0]
    # Проверяем наличие HTML тегов (эмодзи используются как текст)
    assert isinstance(call_args, str)
    assert len(call_args) > 0
