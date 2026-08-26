import logging

from core import ScenarioType, SupportSession
from services.assistant import OpenAISupportAssistant
from services.scenario_router import ScenarioRouter
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)

FINAL_CLIENT_MESSAGE_SUPPORT = (
    "Спасибо! Я передал вашу заявку специалисту. "
    "Мы свяжемся с вами в ближайшее время."
)

FINAL_CLIENT_MESSAGE_SALES = (
    "Спасибо! Я передал вашу заявку менеджеру. "
    "Мы свяжемся с вами в ближайшее время."
)


class SupportWorkflowService:
    def __init__(
        self,
        assistant: OpenAISupportAssistant,
        notifier: OperatorNotifier,
        scenario_router: ScenarioRouter | None = None,
    ) -> None:
        self._assistant = assistant
        self._notifier = notifier
        self._scenario_router = scenario_router or ScenarioRouter()

    async def process_message(self, session: SupportSession, message_text: str) -> str:
        # Если заявка уже отправлена и пользователь пишет снова — начинаем новый диалог
        if session.submitted:
            session.reset()

        # Если сценарий ещё не выбран — обрабатываем выбор
        if not session.scenario:
            scenario = self._scenario_router.resolve(message_text)
            if scenario is None:
                return self._scenario_router.selection_message()
            session.scenario = scenario
            session.started = True
            greeting = self._scenario_router.greeting(scenario)
            session.add_assistant_message(greeting)
            return greeting

        history_before_turn = session.recent_history()
        is_new_session = not history_before_turn and not session.started

        turn = await self._assistant.generate_turn(
            scenario=session.scenario,
            current_ticket=session.ticket,
            current_lead=session.lead,
            user_message=message_text,
            is_new_session=is_new_session,
            conversation_history=history_before_turn,
            last_assistant_message=session.last_assistant_message,
            telegram_first_name=session.telegram_first_name,
        )

        session.add_user_message(message_text)

        if session.scenario == "support":
            session.ticket.merge(turn.extracted_ticket)
        else:
            session.lead.merge(turn.extracted_lead)

        session.started = True

        # Если LLM пропустил важный шаг, переопределяем ответ чётким вопросом
        if session.scenario == "support":
            guard_reply = self._build_support_guard_reply(session)
        else:
            guard_reply = self._build_sales_guard_reply(session)

        if guard_reply is not None:
            session.add_assistant_message(guard_reply)
            return guard_reply

        # Только если guard не сработал и контакт всё ещё не собран — fallback на username
        self._fill_contact_from_telegram_if_missing(session)

        is_complete = self._is_current_object_complete(session)

        # Guard against LLM claiming readiness while required fields are still missing.
        # In that case we ignore ready_to_submit and ask for the next missing field.
        if turn.ready_to_submit and not is_complete:
            logger.warning(
                "LLM said ready_to_submit=true but object is incomplete for user_id=%s. "
                "Forcing guard question.",
                session.user_id,
            )
            if session.scenario == "support":
                guard_reply = self._build_support_guard_reply(session)
            else:
                guard_reply = self._build_sales_guard_reply(session)
            if guard_reply is not None:
                session.add_assistant_message(guard_reply)
                return guard_reply

        should_submit = is_complete and turn.ready_to_submit

        if should_submit:
            await self._submit(session)
            return self._final_message(session)

        if is_complete and not turn.ready_to_submit:
            logger.warning(
                "Object is complete but LLM did not set ready_to_submit for user_id=%s. "
                "Forcing submission.",
                session.user_id,
            )
            await self._submit(session)
            return self._final_message(session)

        session.add_assistant_message(turn.reply)
        return turn.reply

    def _build_support_guard_reply(self, session: SupportSession) -> str | None:
        """Override LLM reply when a required field is clearly missing.

        Runs in strict order: name -> contact -> problem -> occurred_at -> location -> priority.
        This prevents the LLM from skipping a required field even if it decides to move on.
        """
        ticket = session.ticket
        if not ticket.name:
            return "Подскажите, как к вам обращаться?"
        if not ticket.contact:
            return "Оставьте, пожалуйста, контакт для связи: телефон или Telegram."
        if not ticket.problem_summary:
            return "Кратко опишите, пожалуйста, что случилось."
        if not ticket.occurred_at:
            return "Когда началась эта проблема?"
        if not ticket.location:
            return "Где проявляется проблема: на сайте, в приложении, в функции или на устройстве?"
        if not ticket.priority:
            return "Насколько это срочно: срочно, средне или низкий приоритет?"
        return None

    def _build_sales_guard_reply(self, session: SupportSession) -> str | None:
        """Override LLM reply when a required field is clearly missing.

        Company is optional but explicitly asked once. The company_asked flag is set
        before returning the company question so we do not repeat it if the user
        ignores the question.
        """
        lead = session.lead
        if not lead.name:
            return "Подскажите, как к вам обращаться?"
        if not lead.contact:
            return "Оставьте, пожалуйста, контакт для связи: телефон или Telegram."
        if lead.company is None and not session.company_asked:
            session.company_asked = True
            return "Укажите, пожалуйста, название компании, или напишите «для себя»."
        if not lead.service_interest:
            return "Какая услуга или продукт вас интересует?"
        if not lead.budget_range:
            return "В каком диапазоне планируете бюджет?"
        if not lead.timeframe:
            return "Когда планируете начать?"
        if not lead.status:
            return "Уточните, пожалуйста: вы готовы начать сразу, сравниваете варианты или пока только изучаете?"
        return None

    @staticmethod
    def _fill_contact_from_telegram_if_missing(session: SupportSession) -> None:
        """Use Telegram username as a fallback contact only when user did not provide one."""
        if session.scenario == "support" and session.ticket.contact:
            return
        if session.scenario == "sales_lead" and session.lead.contact:
            return
        if session.telegram_username:
            contact = f"@{session.telegram_username}"
            if session.scenario == "support":
                session.ticket.contact = contact
            else:
                session.lead.contact = contact
            logger.info(
                "Using telegram_username as fallback contact for user_id=%s scenario=%s",
                session.user_id,
                session.scenario,
            )

    @staticmethod
    def _is_current_object_complete(session: SupportSession) -> bool:
        if session.scenario == "support":
            return session.ticket.is_complete()
        return session.lead.is_complete()

    async def _submit(self, session: SupportSession) -> None:
        await self._notifier.send(session)
        session.submitted = True
        final_message = self._final_message(session)
        session.add_assistant_message(final_message)
        logger.info(
            "%s submitted for user_id=%s scenario=%s",
            "Ticket" if session.scenario == "support" else "Lead",
            session.user_id,
            session.scenario,
        )

    @staticmethod
    def _final_message(session: SupportSession) -> str:
        if session.scenario == "support":
            return FINAL_CLIENT_MESSAGE_SUPPORT
        return FINAL_CLIENT_MESSAGE_SALES

    def selection_message(self) -> str:
        return self._scenario_router.selection_message()

    async def close(self) -> None:
        await self._assistant.close()
