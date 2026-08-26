"""Tests for the configurable scenario router."""

import pytest

from services.scenario_router import ScenarioRouter


class TestScenarioRouter:
    def test_resolve_support_scenario(self) -> None:
        router = ScenarioRouter()
        assert router.resolve("1") == "support"
        assert router.resolve("1️⃣") == "support"
        assert router.resolve("техподдержка") == "support"
        assert router.resolve("Support") == "support"
        assert router.resolve("  1  ") == "support"

    def test_resolve_sales_scenario(self) -> None:
        router = ScenarioRouter()
        assert router.resolve("2") == "sales_lead"
        assert router.resolve("2️⃣") == "sales_lead"
        assert router.resolve("продажи") == "sales_lead"
        assert router.resolve("SALES") == "sales_lead"
        assert router.resolve("менеджер") == "sales_lead"

    def test_resolve_unknown_input(self) -> None:
        router = ScenarioRouter()
        assert router.resolve("3") is None
        assert router.resolve("hello") is None
        assert router.resolve("") is None

    def test_greeting(self) -> None:
        router = ScenarioRouter()
        assert "техподдержку" in router.greeting("support")
        assert "отдела продаж" in router.greeting("sales_lead")

    def test_greeting_unknown_scenario(self) -> None:
        router = ScenarioRouter()
        with pytest.raises(KeyError):
            router.greeting("unknown")  # type: ignore[arg-type]

    def test_selection_message_contains_both_scenarios(self) -> None:
        router = ScenarioRouter()
        message = router.selection_message()
        assert "Техподдержка" in message
        assert "отдела продаж" in message
        assert "1" in message
        assert "2" in message
