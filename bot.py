#!/usr/bin/env python3
"""Telegram бот для анализа постов из каналов с помощью LLM"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramNetworkError

from config import (
    TELEGRAM_BOT_TOKEN,
    LOG_LEVEL,
    DATA_DIR,
    CACHE_DIR,
    HEALTHCHECK_PORT,
    HEALTHCHECK_ENDPOINT,
)
from aiogram.types import BotCommand
from handlers import channel_handler, start_handler
from utils.http import start_healthcheck_server

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

for d in (DATA_DIR, CACHE_DIR):
    d.mkdir(exist_ok=True)


async def set_commands(bot: Bot):
    """Регистрация команд в меню Telegram"""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="settings", description="Настройки (модель и промпт)"),
        BotCommand(command="prompt", description="Установить промпт"),
        BotCommand(command="model", description="Выбрать модель"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Запуск бота и healthcheck сервера"""
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_handler.router)
    dp.include_router(channel_handler.router)

    await set_commands(bot)

    healthcheck_runner = await start_healthcheck_server(
        port=HEALTHCHECK_PORT, endpoint=HEALTHCHECK_ENDPOINT
    )

    try:
        for attempt in range(1, 6):
            try:
                logger.info("Подключение к Telegram (попытка %d/5)...", attempt)
                await dp.start_polling(bot)
                break
            except TelegramNetworkError:
                if attempt == 5:
                    logger.error("Не удалось подключиться после 5 попыток")
                    raise
                logger.warning("Ошибка, повтор через 10 сек...")
                await asyncio.sleep(10)
    finally:
        await healthcheck_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
