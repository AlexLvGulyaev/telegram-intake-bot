"""Repository contract for persisting Telegram Intake Bot sessions.

The protocol allows swapping in-memory storage (MVP default) with PostgreSQL,
Redis, or any other backend without changing the workflow engine or handlers.
"""

from __future__ import annotations

from typing import Protocol

from core import SupportSession


class SessionRepositoryProtocol(Protocol):
    """Contract for session storage implementations."""

    def get_or_create(
        self,
        user_id: int,
        chat_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> SupportSession:
        """Return an existing session or create a new one for the user."""
        ...

    def reset(self, user_id: int) -> None:
        """Reset the user's active session."""
        ...
