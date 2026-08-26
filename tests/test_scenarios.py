"""Integration tests for bot scenarios without Telegram network calls."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from core import AssistantTurn, SupportSession
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.telegram import OperatorNotifier


def _make_session() -> SupportSession:
    return SupportSession(
        user_id=123456,
        chat_id=123456,
        telegram_username="test_user",
        telegram_first_name="Test",
    )


def _make_turn(scenario: str) -> AssistantTurn:
    turn = AssistantTurn(
        reply="Спасибо! Всё собрано.",
        ready_to_submit=True,
    )
    if scenario == "support":
        turn.extracted_ticket.name = "Александр"
        turn.extracted_ticket.contact = "+79991234567"
        turn.extracted_ticket.problem_summary = "Не включается ноутбук"
        turn.extracted_ticket.occurred_at = "сегодня утром"
        turn.extracted_ticket.location = "ноутбук"
        turn.extracted_ticket.priority = "срочно"
    else:
        turn.extracted_lead.name = "Алексей"
        turn.extracted_lead.contact = "@alexei"
        turn.extracted_lead.company = "ООО Ромашка"
        turn.extracted_lead.service_interest = "Автоматизация продаж"
        turn.extracted_lead.budget_range = "100–200 тыс"
        turn.extracted_lead.timeframe = "В течение недели"
        turn.extracted_lead.status = "теплый"
    return turn


async def _run_support_scenario() -> tuple[SupportSession, list[str]]:
    assistant = MagicMock(spec=OpenAISupportAssistant)
    assistant.generate_turn = AsyncMock(return_value=_make_turn("support"))

    notifier = AsyncMock(spec=OperatorNotifier)
    workflow = SupportWorkflowService(assistant, notifier)

    session = _make_session()
    replies: list[str] = []

    replies.append(await workflow.process_message(session, "1"))
    assert session.scenario == "support"

    replies.append(await workflow.process_message(session, "Александр"))
    assert session.ticket.is_complete()
    assert session.submitted
    notifier.send.assert_awaited_once()

    return session, replies


async def _run_sales_scenario() -> tuple[SupportSession, list[str]]:
    assistant = MagicMock(spec=OpenAISupportAssistant)
    assistant.generate_turn = AsyncMock(return_value=_make_turn("sales_lead"))

    notifier = AsyncMock(spec=OperatorNotifier)
    workflow = SupportWorkflowService(assistant, notifier)

    session = _make_session()
    replies: list[str] = []

    replies.append(await workflow.process_message(session, "2"))
    assert session.scenario == "sales_lead"

    replies.append(await workflow.process_message(session, "Алексей"))
    assert session.lead.is_complete()
    assert session.submitted
    notifier.send.assert_awaited_once()

    return session, replies


def test_support_scenario() -> None:
    session, replies = asyncio.run(_run_support_scenario())
    assert session.scenario == "support"
    assert session.ticket.name == "Александр"
    assert session.ticket.priority == "срочно"
    assert any("специалисту" in r for r in replies)


def test_sales_scenario() -> None:
    session, replies = asyncio.run(_run_sales_scenario())
    assert session.scenario == "sales_lead"
    assert session.lead.name == "Алексей"
    assert session.lead.status == "теплый"
    assert any("менеджеру" in r for r in replies)


if __name__ == "__main__":
    test_support_scenario()
    test_sales_scenario()
    print("ALL_SCENARIO_TESTS_PASSED")
