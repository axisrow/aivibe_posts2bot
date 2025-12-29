"""Integration test that starts the real bot."""

import asyncio
import socket
from contextlib import suppress

import aiohttp
import pytest


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


async def _wait_for_healthcheck(
    task: asyncio.Task, url: str, timeout: float = 10.0
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    async with aiohttp.ClientSession() as session:
        while loop.time() < deadline:
            if task.done():
                exc = task.exception()
                if exc:
                    raise AssertionError(
                        "bot stopped before healthcheck became ready"
                    ) from exc
                raise AssertionError("bot stopped before healthcheck became ready")

            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if text.strip() == "OK":
                            return
            except aiohttp.ClientError:
                pass

            await asyncio.sleep(0.2)

    raise AssertionError(f"healthcheck did not start within {timeout}s: {url}")


@pytest.mark.asyncio
async def test_real_bot_startup(monkeypatch):
    port = _get_free_port()
    endpoint = "/health"

    import bot as bot_module
    token = getattr(bot_module, "TELEGRAM_BOT_TOKEN", "").strip()
    assert token, "TELEGRAM_BOT_TOKEN is required to start the real bot in tests"

    monkeypatch.setattr(bot_module, "HEALTHCHECK_PORT", port)
    monkeypatch.setattr(bot_module, "HEALTHCHECK_ENDPOINT", endpoint)

    task = asyncio.create_task(bot_module.main())
    try:
        await _wait_for_healthcheck(task, f"http://127.0.0.1:{port}{endpoint}")
        assert not task.done(), "bot exited early after startup"
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
