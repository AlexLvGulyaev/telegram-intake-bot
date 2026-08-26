"""Tests for session storage backends."""

from unittest.mock import AsyncMock

import pytest

from core import SupportSession
from services.storage import InMemorySessionRepository
from services.storage.postgres_session_repository import PostgresSessionRepository


class TestInMemorySessionRepository:
    def test_get_or_create_creates_new_session(self) -> None:
        repo = InMemorySessionRepository()
        session = repo.get_or_create(
            user_id=1,
            chat_id=10,
            telegram_username="user",
            telegram_first_name="User",
        )
        assert isinstance(session, SupportSession)
        assert session.user_id == 1
        assert session.chat_id == 10
        assert session.telegram_username == "user"

    def test_get_or_create_returns_existing_session(self) -> None:
        repo = InMemorySessionRepository()
        session1 = repo.get_or_create(
            user_id=1,
            chat_id=10,
            telegram_username="user",
            telegram_first_name="User",
        )
        session2 = repo.get_or_create(
            user_id=1,
            chat_id=20,
            telegram_username="new_user",
            telegram_first_name="New",
        )
        assert session1 is session2
        assert session2.chat_id == 20
        assert session2.telegram_username == "new_user"

    def test_reset_clears_session(self) -> None:
        repo = InMemorySessionRepository()
        session = repo.get_or_create(
            user_id=1,
            chat_id=10,
            telegram_username="user",
            telegram_first_name="User",
        )
        session.scenario = "support"
        session.started = True
        repo.reset(1)
        assert session.scenario is None
        assert session.started is False


class TestPostgresSessionRepositorySerialization:
    def test_serialize_deserialize_roundtrip(self) -> None:
        repo = PostgresSessionRepository("postgresql://localhost/test")
        session = SupportSession(
            user_id=123,
            chat_id=456,
            telegram_username="test_user",
            telegram_first_name="Test",
            scenario="support",
            started=True,
        )
        session.ticket.name = "Александр"
        session.add_user_message("Не работает ноутбук")
        session.add_assistant_message("Как вас зовут?")

        raw = repo._serialize(session)
        restored = repo._deserialize(raw, 123)

        assert restored.user_id == 123
        assert restored.chat_id == 456
        assert restored.telegram_username == "test_user"
        assert restored.scenario == "support"
        assert restored.started is True
        assert restored.ticket.name == "Александр"
        assert len(restored.history) == 2


