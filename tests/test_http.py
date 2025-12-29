"""Тесты для HTTP healthcheck сервера"""

import pytest
from aiohttp import web
from utils.http import health_handler, start_healthcheck_server


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(aiohttp_client):
    """Тест что /health возвращает OK с кодом 200"""
    app = web.Application()
    app.router.add_get("/health", health_handler)

    factory = aiohttp_client
    async for client in factory(app):
        resp = await client.get("/health")

        assert resp.status == 200
        text = await resp.text()
        assert text == "OK"


@pytest.mark.asyncio
async def test_health_endpoint_is_get_only(aiohttp_client):
    """Тест что /health отвечает только на GET запросы"""
    app = web.Application()
    app.router.add_get("/health", health_handler)

    factory = aiohttp_client
    async for client in factory(app):
        # GET должен работать
        resp = await client.get("/health")
        assert resp.status == 200

        # POST должен вернуть 405 (Method Not Allowed)
        resp = await client.post("/health")
        assert resp.status == 405


@pytest.mark.asyncio
async def test_healthcheck_server_starts():
    """Тест запуска healthcheck сервера на произвольном порту"""
    # Используем порт 0 для автоматического выбора свободного порта
    runner = await start_healthcheck_server(port=0)

    try:
        assert runner is not None
        assert isinstance(runner, web.AppRunner)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_healthcheck_server_custom_endpoint(aiohttp_client):
    """Тест healthcheck сервера с кастомным эндпоинтом"""
    endpoint = "/healthz"
    app = web.Application()
    app.router.add_get(endpoint, health_handler)

    factory = aiohttp_client
    async for client in factory(app):
        resp = await client.get(endpoint)

        assert resp.status == 200
        text = await resp.text()
        assert text == "OK"
