"""Сервис для работы с LLM через LangChain + Ollama Cloud"""

import logging
import asyncio
import os
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    OLLAMA_API_KEY,
    DEFAULT_REWRITE_PROMPT,
)

logger = logging.getLogger(__name__)

# Установка переменной окружения для автоматической аутентификации
if OLLAMA_API_KEY:
    os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY


async def rewrite_post(
    post: dict, custom_prompt: Optional[str] = None, model: Optional[str] = None
) -> str:
    """Рерайтит пост через LLM с пользовательским промптом и моделью"""
    if not (text := post.get("text", "")) or len(text) < 10:
        return "Пост слишком короткий для рерайта"

    current_model = model or OLLAMA_MODEL
    current_llm = ChatOllama(
        base_url=OLLAMA_BASE_URL, model=current_model, temperature=LLM_TEMPERATURE
    )

    prompt = ChatPromptTemplate.from_template(
        "{instruction}\n\nОригинальный пост:\n{text}\n\nРерайт:"
    )

    try:
        result = await asyncio.to_thread(
            (prompt | current_llm).invoke,
            {"instruction": custom_prompt or DEFAULT_REWRITE_PROMPT, "text": text},
        )
        return (
            result.content.strip()
            if isinstance(result.content, str)
            else str(result.content)
        )
    except Exception as e:
        logger.error(
            "Rewrite error for post %s (model %s): %s",
            post.get("post_link"),
            current_model,
            e,
        )
        return "[Ошибка рерайта: %s]" % e
