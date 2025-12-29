"""HTTP сервер для healthcheck эндпоинта"""

from aiohttp import web
import logging

logger = logging.getLogger(__name__)


async def health_handler(_request):
    """Обработчик healthcheck запроса"""
    return web.Response(text="OK", status=200)


async def start_healthcheck_server(port: int = 8080, endpoint: str = "/health"):
    """Запуск HTTP сервера для healthcheck"""
    app = web.Application()
    app.router.add_get(endpoint, health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()

    logger.info("Healthcheck сервер запущен на порту %s, эндпоинт: %s", port, endpoint)
    return runner
