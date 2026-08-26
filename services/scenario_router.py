"""Configurable scenario selection for Telegram Intake Bot.

Adding a new scenario should require only three changes:
1. Create a prompt file at prompts/<scenario>-assistant-v1.md.
2. Add the scenario to the registry below with synonyms and a greeting.
3. Extend ASSISTANT_RESPONSE_SCHEMA in services/assistant/prompts.py if new
   fields are needed.

The workflow engine remains generic: it resolves the scenario, stores it in
SupportSession.scenario, and continues with the existing guard/save flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core import ScenarioType


@dataclass(frozen=True)
class _ScenarioConfig:
    """Static configuration for one selectable scenario."""

    scenario: ScenarioType
    display_name: str
    synonyms: tuple[str, ...]
    greeting: str


DEFAULT_SELECTION_MESSAGE = (
    "Здравствуйте! Я AI-ассистент. Выберите, чем могу помочь:\n\n"
    "1️⃣ Техподдержка — оформить заявку в поддержку\n"
    "2️⃣ Заявка для отдела продаж — собрать заявку для менеджера\n\n"
    "Напишите 1 или 2."
)


_SCENARIO_REGISTRY: tuple[_ScenarioConfig, ...] = (
    _ScenarioConfig(
        scenario="support",
        display_name="Техподдержка",
        synonyms=("1", "1️⃣", "поддержка", "техподдержка", "тех поддержка", "support"),
        greeting="Здравствуйте! Я помогу вам с обращением в техподдержку. Как вас зовут?",
    ),
    _ScenarioConfig(
        scenario="sales_lead",
        display_name="Заявка для отдела продаж",
        synonyms=("2", "2️⃣", "продажи", "заявка", "менеджер", "sales", "лид"),
        greeting="Здравствуйте! Я помогу оформить заявку для отдела продаж. Как вас зовут?",
    ),
)

# Map each synonym to its config for O(1) lookup.
_SYNONYM_INDEX: dict[str, _ScenarioConfig] = {}
for _cfg in _SCENARIO_REGISTRY:
    for _syn in _cfg.synonyms:
        _SYNONYM_INDEX[_syn] = _cfg


class ScenarioRouter:
    """Resolves free-form user input into a known scenario."""

    def __init__(
        self,
        registry: tuple[_ScenarioConfig, ...] | None = None,
        selection_message: str | None = None,
        normalize: Callable[[str], str] | None = None,
    ) -> None:
        self._registry = registry or _SCENARIO_REGISTRY
        self._selection_message = selection_message or DEFAULT_SELECTION_MESSAGE
        self._normalize = normalize or self._default_normalize
        self._index = self._build_index(self._registry)

    @staticmethod
    def _default_normalize(text: str) -> str:
        return text.strip().lower()

    @staticmethod
    def _build_index(
        registry: tuple[_ScenarioConfig, ...],
    ) -> dict[str, _ScenarioConfig]:
        index: dict[str, _ScenarioConfig] = {}
        for cfg in registry:
            for syn in cfg.synonyms:
                index[syn] = cfg
        return index

    def resolve(self, message_text: str) -> ScenarioType | None:
        """Return the scenario for a user message, or None if not recognized."""
        normalized = self._normalize(message_text)
        cfg = self._index.get(normalized)
        return cfg.scenario if cfg else None

    def greeting(self, scenario: ScenarioType) -> str:
        """Return the first greeting for a scenario."""
        for cfg in self._registry:
            if cfg.scenario == scenario:
                return cfg.greeting
        raise KeyError(f"Unknown scenario: {scenario}")

    def selection_message(self) -> str:
        return self._selection_message

    def known_scenarios(self) -> tuple[ScenarioType, ...]:
        return tuple(cfg.scenario for cfg in self._registry)
