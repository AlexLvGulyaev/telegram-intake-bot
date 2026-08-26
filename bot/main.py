import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.handlers import router
from core import get_settings, setup_logging
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.storage import InMemorySessionRepository
from services.storage.postgres_session_repository import PostgresSessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


def build_session_repository(settings):
    """Create the configured session repository backend."""
    if settings.session_storage_type.lower() == "postgres":
        if not settings.database_url:
            raise ValueError(
                "DATABASE_URL is required when SESSION_STORAGE_TYPE=postgres"
            )
        return PostgresSessionRepository(settings.database_url)
    return InMemorySessionRepository()


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties())
    session_repository = build_session_repository(settings)
    assistant = OpenAISupportAssistant(settings)
    notifier = OperatorNotifier(bot, settings)
    workflow = SupportWorkflowService(
        assistant=assistant,
        notifier=notifier,
        scenario_router=None,  # default router is created inside the service
    )

    dp = Dispatcher()
    dp.include_router(router)
    dp["session_repository"] = session_repository
    dp["workflow"] = workflow

    logger.info(
        "Starting support intake bot (session_storage=%s)",
        settings.session_storage_type,
    )
    try:
        await dp.start_polling(bot)
    finally:
        await workflow.close()
        if hasattr(session_repository, "close"):
            await session_repository.close()
        await bot.session.close()
