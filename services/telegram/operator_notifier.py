from aiogram import Bot

from core import SalesLead, ScenarioType, Settings, SupportSession, SupportTicket


class OperatorNotifier:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send(self, session: SupportSession) -> None:
        scenario = session.scenario or "support"
        if scenario == "sales_lead":
            text = self._format_lead(session)
        else:
            text = self._format_ticket(session)
        await self._bot.send_message(self._settings.operator_chat_id, text)

    @staticmethod
    def _format_ticket(session: SupportSession) -> str:
        ticket = session.ticket
        assert ticket is not None
        return _render(
            title="=== НОВАЯ ЗАЯВКА В ТП ===",
            fields=[
                ("Имя", ticket.name),
                ("Контакт", ticket.contact),
                ("Проблема", ticket.problem_summary, True),
                ("Когда возникло", ticket.occurred_at),
                ("Где", ticket.location),
                ("Приоритет", ticket.priority),
            ],
            footer=_user_footer(session),
        )

    @staticmethod
    def _format_lead(session: SupportSession) -> str:
        lead = session.lead
        assert lead is not None
        return _render(
            title="=== НОВЫЙ ЛИД ===",
            fields=[
                ("Имя", lead.name),
                ("Контакт", lead.contact),
                ("Компания", lead.company or "—"),
                ("Интерес", lead.service_interest, True),
                ("Бюджет", lead.budget_range),
                ("Сроки", lead.timeframe),
                ("Статус", lead.status),
            ],
            footer=_user_footer(session),
        )


def _render(
    title: str,
    fields: list[tuple[str, str | None, bool] | tuple[str, str | None]],
    footer: list[str],
) -> str:
    lines: list[str] = [title, ""]
    for field in fields:
        if len(field) == 3:
            label, value, multiline = field  # type: ignore[assignment]
        else:
            label, value = field  # type: ignore[assignment]
            multiline = False
        rendered_value = value or "—"
        if multiline:
            lines.append(f"{label}:")
            lines.append(rendered_value)
            lines.append("")
        else:
            lines.append(f"{label}: {rendered_value}")
    lines.extend(["", *footer, "", "=== КОНЕЦ ==="])
    return "\n".join(lines)


def _user_footer(session: SupportSession) -> list[str]:
    return [
        f"Telegram user id: {session.user_id}",
        (
            f"Telegram username: @{session.telegram_username}"
            if session.telegram_username
            else "Telegram username: -"
        ),
    ]
