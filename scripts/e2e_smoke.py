"""Backend E2E smoke for Telegram Intake Bot.

Exercises the real LLM and real Telegram outbound notification path
without relying on a human Telegram client. The script simulates a user
conversation by calling SupportWorkflowService directly, then sends the
resulting ticket/lead to the configured OPERATOR_CHAT_ID via the real Bot API.

Run from the case directory with the venv and .env loaded:
    source .venv/bin/activate && source .env && python scripts/e2e_smoke.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Make the documented run line work from the case directory:
# `python scripts/e2e_smoke.py` (script dir, not repo root, is on sys.path)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from core import ScenarioType, Settings, SupportSession, get_settings, setup_logging
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.scenario_router import ScenarioRouter
from services.storage import InMemorySessionRepository
from services.storage.postgres_session_repository import PostgresSessionRepository
from services.telegram import OperatorNotifier
from bot.main import build_session_repository

logger = logging.getLogger(__name__)


class _CapturedBot(Bot):
    """Real aiogram Bot that records every outgoing text message."""

    def __init__(self, token: str, **kwargs: Any) -> None:
        super().__init__(token, **kwargs)
        self.sent_messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int | str, text: str, **kwargs: Any) -> Any:
        self.sent_messages.append((chat_id, text))
        return await super().send_message(chat_id, text, **kwargs)


def _make_session(user_id: int = 999999001) -> SupportSession:
    repo = InMemorySessionRepository()
    return repo.get_or_create(
        user_id=user_id,
        chat_id=user_id,
        telegram_username="e2e_test_user",
        telegram_first_name="E2E",
    )


async def _load_or_create_session(
    repo: InMemorySessionRepository,
    user_id: int,
) -> SupportSession:
    """Load a persisted session or create a fresh one when using Postgres."""
    if hasattr(repo, "get_or_create") and asyncio.iscoroutinefunction(repo.get_or_create):
        return await repo.get_or_create(
            user_id=user_id,
            chat_id=user_id,
            telegram_username="e2e_test_user",
            telegram_first_name="E2E",
        )
    return repo.get_or_create(
        user_id=user_id,
        chat_id=user_id,
        telegram_username="e2e_test_user",
        telegram_first_name="E2E",
    )


async def _save_if_persistent(repo: InMemorySessionRepository, session: SupportSession) -> None:
    """Save session state when the repository supports persistence."""
    if hasattr(repo, "save") and asyncio.iscoroutinefunction(repo.save):
        await repo.save(session)


async def _reset_if_persistent(repo: InMemorySessionRepository, user_id: int) -> None:
    """Reset session state when the repository supports persistence."""
    if hasattr(repo, "reset") and asyncio.iscoroutinefunction(repo.reset):
        await repo.reset(user_id)


async def _run_support_scenario(
    workflow: SupportWorkflowService,
    repo: InMemorySessionRepository,
) -> SupportSession:
    await _reset_if_persistent(repo, 999999001)
    session = await _load_or_create_session(repo, 999999001)
    replies: list[str] = []

    # Scenario selection
    replies.append(await workflow.process_message(session, "1"))
    await _save_if_persistent(repo, session)

    # Provide all required fields
    turns = [
        "Меня зовут Иван",
        "Контакт: +7-900-123-45-67",
        "Сайт не открывается, страница зависает",
        "Началось сегодня утром",
        "Проблема на сайте в личном кабинете",
        "Срочно",
        "Да, отправьте",
    ]
    for text in turns:
        # Reload to simulate independent request per message
        if hasattr(repo, "get_or_create") and asyncio.iscoroutinefunction(repo.get_or_create):
            session = await _load_or_create_session(repo, 999999001)
        reply = await workflow.process_message(session, text)
        replies.append(reply)
        await _save_if_persistent(repo, session)
        if session.submitted:
            break

    return session, replies


async def _run_sales_scenario(
    workflow: SupportWorkflowService,
    repo: InMemorySessionRepository,
) -> SupportSession:
    await _reset_if_persistent(repo, 999999002)
    session = await _load_or_create_session(repo, 999999002)
    session.scenario = "sales_lead"  # skip router for direct scenario test
    session.started = True
    await _save_if_persistent(repo, session)
    replies: list[str] = []

    turns = [
        "Привет, хочу узнать про внедрение бота",
        "Меня зовут Анна",
        "Telegram: @anna_sales",
        "Компания ООО Демо",
        "Интересует автоматизация продаж в Telegram",
        "Бюджет до 200 тыс. руб.",
        "Начать хочу в сентябре",
        "Готовы начать, сравниваем варианты",
        "Да, оформите заявку",
    ]
    for text in turns:
        if hasattr(repo, "get_or_create") and asyncio.iscoroutinefunction(repo.get_or_create):
            session = await _load_or_create_session(repo, 999999002)
        reply = await workflow.process_message(session, text)
        replies.append(reply)
        await _save_if_persistent(repo, session)
        if session.submitted:
            break

    return session, replies


def _format_log(scenario: ScenarioType, replies: list[str], sent: list[tuple[int, str]]) -> str:
    lines = [f"=== {scenario.upper()} E2E SMOKE ===", ""]
    lines.append("Bot replies to user:")
    for i, reply in enumerate(replies, 1):
        lines.append(f"  {i}. {reply[:300]}{'...' if len(reply) > 300 else ''}")
    lines.append("")
    lines.append("Telegram notifications sent:")
    for chat_id, text in sent:
        lines.append(f"  chat_id={chat_id}")
        lines.append(f"  {text[:500]}{'...' if len(text) > 500 else ''}")
    return "\n".join(lines)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    bot = _CapturedBot(settings.telegram_bot_token, default=DefaultBotProperties())
    assistant = OpenAISupportAssistant(settings)
    notifier = OperatorNotifier(bot, settings)
    workflow = SupportWorkflowService(
        assistant=assistant,
        notifier=notifier,
        scenario_router=ScenarioRouter(),
    )
    repo = build_session_repository(settings)

    try:
        support_session, support_replies = await _run_support_scenario(workflow, repo)
        logger.info(_format_log("support", support_replies, bot.sent_messages))
        assert support_session.submitted, "Support scenario did not submit"
        assert support_session.ticket.is_complete(), "Support ticket is incomplete"

        # Verify session was persisted after support scenario
        if hasattr(repo, "get_or_create") and asyncio.iscoroutinefunction(repo.get_or_create):
            persisted = await repo.get_or_create(999999001, 999999001, "e2e_test_user", "E2E")
            assert persisted.submitted, "Support session was not persisted as submitted"
            assert persisted.ticket.is_complete(), "Persisted support ticket is incomplete"

        # Reset captured messages between scenarios
        bot.sent_messages.clear()

        sales_session, sales_replies = await _run_sales_scenario(workflow, repo)
        logger.info(_format_log("sales", sales_replies, bot.sent_messages))
        assert sales_session.submitted, "Sales scenario did not submit"
        assert sales_session.lead.is_complete(), "Sales lead is incomplete"

        # Verify session was persisted after sales scenario
        if hasattr(repo, "get_or_create") and asyncio.iscoroutinefunction(repo.get_or_create):
            persisted = await repo.get_or_create(999999002, 999999002, "e2e_test_user", "E2E")
            assert persisted.submitted, "Sales session was not persisted as submitted"
            assert persisted.lead.is_complete(), "Persisted sales lead is incomplete"

        logger.info("=== E2E SMOKE PASSED ===")
    finally:
        await workflow.close()
        if hasattr(repo, "close") and asyncio.iscoroutinefunction(repo.close):
            await repo.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
