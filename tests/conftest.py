"""Pytest конфигурация и фикстуры для тестирования бота"""

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def bot():
    """Мок Bot для тестирования"""
    bot = MagicMock(spec=Bot)
    bot.token = "TEST_TOKEN"
    return bot


@pytest.fixture
def dp():
    """Dispatcher с MemoryStorage для тестирования"""
    storage = MemoryStorage()
    return Dispatcher(storage=storage)


@pytest.fixture
def mock_message():
    """Мок Message для тестирования handlers"""
    message = AsyncMock()
    message.from_user.id = 123456
    message.from_user.first_name = "TestUser"
    message.text = "/start"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Мок FSMContext для тестирования состояний"""
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def aiohttp_client():
    """Фикстура для создания тестового aiohttp клиента"""
    from aiohttp.test_utils import TestClient, TestServer

    async def factory(app):
        server = TestServer(app)
        client = TestClient(server)

        await client.start_server()
        yield client
        await client.close()

    return factory
