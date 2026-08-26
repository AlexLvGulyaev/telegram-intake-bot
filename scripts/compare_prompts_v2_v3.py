"""Compare TIB prompt versions v2 and v3 through the full workflow.

This script runs real OpenAI API calls through SupportWorkflowService, so it
exercises both the prompt AND the guard/fallback layers. Run from the project
root with:
    source .venv/bin/activate
    python scripts/compare_prompts_v2_v3.py

The markdown report is printed to stdout and should be pasted into
docs/TESTING.md section 7.6.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock

from dotenv import load_dotenv

# Load project modules
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Settings, SupportSession
from services import SupportWorkflowService
from services.assistant import OpenAISupportAssistant
from services.telegram import OperatorNotifier

load_dotenv()


@dataclass
class EvaluatedTurn:
    user_message: str
    bot_reply: str
    submitted: bool
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def make_settings(prompt_version: str) -> Settings:
    """Build settings that force OpenAISupportAssistant to load a specific prompt version.

    We temporarily swap the prompt files on disk so _load_prompt picks up v2 or v3.
    The original active files are restored after the run.
    """
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "test"),
        operator_chat_id=int(os.getenv("OPERATOR_CHAT_ID", "0")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        log_level="INFO",
    )


async def run_scenario(
    workflow: SupportWorkflowService,
    assistant: OpenAISupportAssistant,
    scenario: str,
    user_messages: list[str],
) -> tuple[list[EvaluatedTurn], SupportSession]:
    session = SupportSession(
        user_id=123456,
        chat_id=123456,
        telegram_username="test_user",
        telegram_first_name="Test",
    )

    # Track per-turn metrics via a monkeypatched _post_with_retries
    metrics = {"latency_ms": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    original_post = assistant._post_with_retries

    async def _instrumented_post(payload: dict):
        import time
        start = time.perf_counter()
        response = await original_post(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json()
        usage = data.get("usage", {})
        metrics["latency_ms"] = elapsed_ms
        metrics["prompt_tokens"] = usage.get("prompt_tokens", 0)
        metrics["completion_tokens"] = usage.get("completion_tokens", 0)
        metrics["total_tokens"] = usage.get("total_tokens", 0)
        return response

    assistant._post_with_retries = _instrumented_post

    # First message selects scenario via the workflow selection handler
    selection_msg = "1" if scenario == "support" else "2"
    await workflow.process_message(session, selection_msg)

    turns: list[EvaluatedTurn] = []
    for msg in user_messages:
        # Reset metrics for this turn
        metrics.update({"latency_ms": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        reply = await workflow.process_message(session, msg)
        turns.append(EvaluatedTurn(
            user_message=msg,
            bot_reply=reply,
            submitted=session.submitted,
            latency_ms=metrics["latency_ms"],
            prompt_tokens=metrics["prompt_tokens"],
            completion_tokens=metrics["completion_tokens"],
            total_tokens=metrics["total_tokens"],
        ))
        if session.submitted:
            break

    assistant._post_with_retries = original_post
    return turns, session


SCENARIOS = {
    "S1 support ideal": (
        "support",
        [
            "Александр",
            "+79991234567",
            "Не включается ноутбук после обновления",
            "сегодня утром",
            "на ноутбуке",
            "срочно",
        ],
    ),
    "S2 support shuffled": (
        "support",
        [
            "Не работает касса, помогите",
            "Меня зовут Игорь",
            "+79001234567",
            "с утра",
            "в кассовом ПО",
            "срочно",
        ],
    ),
    "S3 sales ideal": (
        "sales_lead",
        [
            "Алексей",
            "@alexei_sales",
            "ООO Ромашка",
            "Автоматизация продаж",
            "100–200 тыс",
            "в течение недели",
        ],
    ),
    "S4 sales skip company": (
        "sales_lead",
        [
            "Мария",
            "+79112223344",
            "для себя",
            "Настройка Telegram-бота",
            "до 50 тыс",
            "сразу",
        ],
    ),
}


def swap_prompts(version: str) -> None:
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    for scenario in ("support", "sales-lead"):
        active = prompts_dir / f"{scenario}-assistant-v3.md"
        backup = prompts_dir / f"{scenario}-assistant-v3.md.active"
        target = prompts_dir / f"{scenario}-assistant-{version}.md"

        # Save current active (v3) content
        backup.write_bytes(active.read_bytes())
        # Replace with target version content
        active.write_bytes(target.read_bytes())


def restore_prompts(version: str) -> None:
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    for scenario in ("support", "sales-lead"):
        active = prompts_dir / f"{scenario}-assistant-v3.md"
        backup = prompts_dir / f"{scenario}-assistant-v3.md.active"
        active.write_bytes(backup.read_bytes())
        backup.unlink()


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set")
        return

    results: dict[str, dict[str, tuple[list[EvaluatedTurn], SupportSession]]] = {}

    for version in ("v2", "v3"):
        swap_prompts(version)
        try:
            settings = make_settings(version)
            assistant = OpenAISupportAssistant(settings)
            notifier = AsyncMock(spec=OperatorNotifier)
            workflow = SupportWorkflowService(assistant, notifier)

            results[version] = {}
            for scenario_name, (scenario, messages) in SCENARIOS.items():
                history, session = await run_scenario(workflow, assistant, scenario, messages)
                results[version][scenario_name] = (history, session)

            await assistant.close()
        finally:
            restore_prompts(version)

    # Print markdown report
    print("# LLM-сравнение промптов v2 vs v3 (через SupportWorkflowService)\n")
    print(f"**Модель:** {os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')}")
    print(f"**Temperature:** 0.2")
    print(f"**Окружение:** реальный OpenAI API + guard-слой + fallback\n")

    print("| Сценарий | Версия | Собрано | Ложный ready | Guard | Отправлено | Ср. длина reply | Ср. latency | Ср. prompt tokens | Ср. completion tokens | Ср. total tokens | Примечания |")
    print("|----------|--------|---------|--------------|-------|------------|-----------------|-------------|-------------------|----------------------|------------------|------------|")

    for scenario_name in SCENARIOS:
        for version in ("v2", "v3"):
            history, session = results[version][scenario_name]
            if session.scenario == "support":
                obj = session.ticket
            else:
                obj = session.lead
            is_complete = obj.is_complete()
            submitted = session.submitted
            false_ready = any(t.submitted and not is_complete for t in history)
            avg_len = sum(len(t.bot_reply) for t in history) / len(history)
            avg_latency = sum(t.latency_ms for t in history) / len(history)
            avg_prompt = sum(t.prompt_tokens for t in history) / len(history)
            avg_completion = sum(t.completion_tokens for t in history) / len(history)
            avg_total = sum(t.total_tokens for t in history) / len(history)
            guard_used = any(
                any(phrase in t.bot_reply for phrase in [
                    "Подскажите, как к вам обращаться",
                    "Оставьте, пожалуйста, контакт",
                    "кратко опишите",
                    "Когда началась",
                    "Где проявляется",
                    "Насколько это срочно",
                    "название компании",
                    "Какая услуга",
                    "диапазоне планируете",
                    "Когда планируете",
                    "готовы начать сразу",
                ])
                for t in history
            )
            notes = ""
            if not submitted and is_complete:
                notes = "Поля собраны, но не отправлено"
            elif submitted and not is_complete:
                notes = "Отправлено неполное!"

            print(
                f"| {scenario_name} | {version} | "
                f"{'✅' if is_complete else '❌'} | "
                f"{'❌' if false_ready else '—'} | "
                f"{'✅' if guard_used else '—'} | "
                f"{'✅' if submitted else '❌'} | "
                f"{avg_len:.0f} | "
                f"{avg_latency:.0f} ms | "
                f"{avg_prompt:.0f} | "
                f"{avg_completion:.0f} | "
                f"{avg_total:.0f} | "
                f"{notes} |"
            )

    print("\n## Детальные переписки\n")
    for scenario_name in SCENARIOS:
        print(f"### {scenario_name}\n")
        for version in ("v2", "v3"):
            print(f"**{version}:**\n")
            history, session = results[version][scenario_name]
            if session.scenario == "support":
                obj = session.ticket
            else:
                obj = session.lead
            for i, t in enumerate(history, 1):
                print(f"{i}. Пользователь: {t.user_message}")
                print(f"   Бот: {t.bot_reply}")
                print(f"   submitted={t.submitted}")
            print(f"   **Итог:** {obj.model_dump()}\n")


if __name__ == "__main__":
    asyncio.run(main())
