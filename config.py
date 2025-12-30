"""Конфигурация бота и LLM"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

# Telegram Bot (из .env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Ollama Cloud + LangChain
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")  # из .env
OLLAMA_BASE_URL = "https://ollama.com"
AVAILABLE_MODELS = [
    "gpt-oss:120b-cloud",
    "gemini-3-flash-preview:cloud",
    "deepseek-v3.2:cloud",
    "glm-4.7:cloud",
    "minimax-m2.1:cloud",
]
OLLAMA_MODEL = AVAILABLE_MODELS[0]
LLM_TEMPERATURE = 1.0
LLM_TIMEOUT = 120  # секунды

# Парсер настройки
MAX_PAGES_PER_REQUEST = 3
INCLUDE_FORWARDED_POSTS = True

# Telegram лимиты
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024  # подпись для фото/видео
MAX_POSTS_IN_SUMMARY = 20

# Рерайтинг постов
DEFAULT_REWRITE_PROMPT = "Перепиши пост простыми словами. Выдавай только текст рерайта, без форматирования Markdown, без заголовков и без лишних символов, но с разбивкой на абзацы."

# Логирование
LOG_LEVEL = "INFO"

# Healthcheck сервер
HEALTHCHECK_PORT = int(8080)
HEALTHCHECK_ENDPOINT = "/health"
