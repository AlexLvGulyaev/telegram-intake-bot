"""PostgreSQL-backed session storage for Telegram Intake Bot.

Session state is serialized to JSONB so the repository can persist arbitrary
SupportSession fields without schema migrations for every new guard flag.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core import SupportSession

logger = logging.getLogger(__name__)


class PostgresSessionRepository:
    """PostgreSQL session storage using asyncpg.

    Satisfies SessionRepositoryProtocol. Requires the `tib_sessions` table
    (see docs/schema.sql).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any | None = None

    async def _get_pool(self) -> Any:
        """Lazy asyncpg pool creation."""
        if self._pool is None:
            import asyncpg  # type: ignore[import-untyped]

            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        return self._pool

    def _serialize(self, session: SupportSession) -> str:
        return session.model_dump_json(ensure_ascii=False)

    def _deserialize(self, raw: str, user_id: int) -> SupportSession:
        data = json.loads(raw)
        data["user_id"] = user_id
        return SupportSession.model_validate(data)

    async def get_or_create(
        self,
        user_id: int,
        chat_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> SupportSession:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state FROM tib_sessions WHERE user_id = $1",
                user_id,
            )
            if row is not None and row["state"]:
                session = self._deserialize(row["state"], user_id)
                session.chat_id = chat_id
                session.telegram_username = telegram_username
                session.telegram_first_name = telegram_first_name
                return session

            session = SupportSession(
                user_id=user_id,
                chat_id=chat_id,
                telegram_username=telegram_username,
                telegram_first_name=telegram_first_name,
            )
            await conn.execute(
                """
                INSERT INTO tib_sessions (user_id, state)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (user_id) DO UPDATE SET state = EXCLUDED.state
                """,
                user_id,
                self._serialize(session),
            )
            return session

    async def save(self, session: SupportSession) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tib_sessions (user_id, state)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (user_id) DO UPDATE SET state = EXCLUDED.state
                """,
                session.user_id,
                self._serialize(session),
            )

    async def reset(self, user_id: int) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM tib_sessions WHERE user_id = $1",
                user_id,
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
