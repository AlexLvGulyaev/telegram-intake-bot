import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_prompt(filename: str) -> str:
    """Load a prompt from the prompts/ directory next to the project root."""
    prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
    path = prompts_dir / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.error("Prompt file not found: %s", path)
        raise


SUPPORT_ASSISTANT_PROMPT = _load_prompt("support-assistant-v3.md")
SALES_LEAD_ASSISTANT_PROMPT = _load_prompt("sales-lead-assistant-v3.md")


ASSISTANT_RESPONSE_SCHEMA = {
    "name": "assistant_turn",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "extracted_ticket": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "contact": {"type": ["string", "null"]},
                    "problem_summary": {"type": ["string", "null"]},
                    "occurred_at": {"type": ["string", "null"]},
                    "location": {"type": ["string", "null"]},
                    "priority": {
                        "type": ["string", "null"],
                        "enum": ["срочно", "средне", "низкий приоритет", None],
                    },
                },
                "required": [
                    "name",
                    "contact",
                    "problem_summary",
                    "occurred_at",
                    "location",
                    "priority",
                ],
                "additionalProperties": False,
            },
            "extracted_lead": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "contact": {"type": ["string", "null"]},
                    "company": {"type": ["string", "null"]},
                    "service_interest": {"type": ["string", "null"]},
                    "budget_range": {"type": ["string", "null"]},
                    "timeframe": {"type": ["string", "null"]},
                    "status": {
                        "type": ["string", "null"],
                        "enum": ["горячий", "теплый", "холодный", None],
                    },
                },
                "required": [
                    "name",
                    "contact",
                    "company",
                    "service_interest",
                    "budget_range",
                    "timeframe",
                    "status",
                ],
                "additionalProperties": False,
            },
            "ready_to_submit": {"type": "boolean"},
        },
        "required": ["reply", "extracted_ticket", "extracted_lead", "ready_to_submit"],
        "additionalProperties": False,
    },
}
