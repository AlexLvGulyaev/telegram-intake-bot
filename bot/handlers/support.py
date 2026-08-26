import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from core import SupportSession
from services import SupportWorkflowService
from services.storage import InMemorySessionRepository

logger = logging.getLogger(__name__)
router = Router()

GENERIC_ERROR_MESSAGE = "Сейчас не удалось обработать обращение. Попробуйте еще раз через пару минут."
UNSUPPORTED_MESSAGE = "Пожалуйста, ответьте текстом."


def _is_async_repo(session_repository: InMemorySessionRepository) -> bool:
    """Return True if the repository exposes async persistence methods."""
    return hasattr(session_repository, "save") and asyncio.iscoroutinefunction(
        session_repository.save
    )


async def _repo_get_or_create(
    session_repository: InMemorySessionRepository,
    user_id: int,
    chat_id: int,
    telegram_username: str | None,
    telegram_first_name: str | None,
) -> SupportSession:
    """Load or create a session, handling both sync and async repositories."""
    if _is_async_repo(session_repository):
        return await session_repository.get_or_create(
            user_id=user_id,
            chat_id=chat_id,
            telegram_username=telegram_username,
            telegram_first_name=telegram_first_name,
        )
    return session_repository.get_or_create(
        user_id=user_id,
        chat_id=chat_id,
        telegram_username=telegram_username,
        telegram_first_name=telegram_first_name,
    )


async def _repo_reset(session_repository: InMemorySessionRepository, user_id: int) -> None:
    """Reset session storage, handling both sync and async repositories."""
    if _is_async_repo(session_repository):
        await session_repository.reset(user_id)
    else:
        session_repository.reset(user_id)


async def _repo_save(
    session_repository: InMemorySessionRepository, session: SupportSession
) -> None:
    """Persist session if repository supports it, handling async variants."""
    if _is_async_repo(session_repository):
        await session_repository.save(session)


@router.message(Command("start"))
async def handle_start(
    message: Message,
    session_repository: InMemorySessionRepository,
    workflow: SupportWorkflowService,
) -> None:
    logger.info("handle_start called for user_id=%s", message.from_user.id if message.from_user else None)
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя. Попробуйте еще раз.")
        return

    try:
        session = await _repo_get_or_create(
            session_repository,
            user_id=user.id,
            chat_id=message.chat.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
        )
    except Exception:
        logger.exception("Failed to get_or_create session in handle_start")
        await message.answer(GENERIC_ERROR_MESSAGE)
        return

    try:
        session.reset()
        session.started = True

        selection_message = workflow.selection_message()
        session.add_assistant_message(selection_message)
        await message.answer(selection_message)
        await _repo_save(session_repository, session)
    except Exception:
        logger.exception("Failed to handle /start")
        await message.answer(GENERIC_ERROR_MESSAGE)


@router.message(Command("reset"))
async def handle_reset(
    message: Message,
    session_repository: InMemorySessionRepository,
    workflow: SupportWorkflowService,
) -> None:
    logger.info("handle_reset called for user_id=%s", message.from_user.id if message.from_user else None)
    user = message.from_user
    if user is None:
        await message.answer("Не удалось сбросить диалог. Попробуйте еще раз.")
        return

    try:
        selection_message = workflow.selection_message()
        reset_message = "Диалог сброшен. Давайте начнём заново.\n\n" + selection_message

        await _repo_reset(session_repository, user.id)

        session = await _repo_get_or_create(
            session_repository,
            user_id=user.id,
            chat_id=message.chat.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
        )
        session.started = True

        session.add_assistant_message(reset_message)
        await message.answer(reset_message)
        await _repo_save(session_repository, session)
    except Exception:
        logger.exception("Failed to handle /reset")
        await message.answer(GENERIC_ERROR_MESSAGE)


@router.message(F.text)
async def handle_text_message(
    message: Message,
    session_repository: InMemorySessionRepository,
    workflow: SupportWorkflowService,
) -> None:
    logger.info("handle_text_message called for user_id=%s text=%r", message.from_user.id if message.from_user else None, message.text)
    user = message.from_user
    if user is None or not message.text:
        await message.answer("Не удалось обработать сообщение. Попробуйте еще раз.")
        return

    try:
        session: SupportSession = await _repo_get_or_create(
            session_repository,
            user_id=user.id,
            chat_id=message.chat.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
        )
    except Exception:
        logger.exception("Failed to get_or_create session in handle_text_message")
        await message.answer(GENERIC_ERROR_MESSAGE)
        return

    try:
        reply = await workflow.process_message(session, message.text)
        await message.answer(reply)
    except Exception:
        logger.exception("Failed to process incoming message")
        await message.answer(GENERIC_ERROR_MESSAGE)

    await _repo_save(session_repository, session)


@router.message()
async def handle_unsupported_message(message: Message) -> None:
    logger.info("handle_unsupported_message called")
    await message.answer(UNSUPPORTED_MESSAGE)
