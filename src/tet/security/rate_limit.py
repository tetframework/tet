import logging
import typing as tp

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from pyramid.request import Request
from pyramid_di import RequestScopedBaseService, autowired

from tet.security.config import UTC

logger = logging.getLogger(__name__)


class TetRateLimitService(RequestScopedBaseService):
    session: Session = autowired(Session)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.rate_limit_model: tp.Any = getattr(
            self.registry, "tet_auth_rate_limit_model", None
        )

    @property
    def enabled(self) -> bool:
        return self.rate_limit_model is not None

    def check_rate_limit(
        self, key: str, max_attempts: int, window_seconds: int
    ) -> bool:
        """Record an attempt and return True if the rate limit is exceeded.

        Uses a separate connection so the record survives transaction rollback
        (e.g. on a 401 response).
        """
        if not self.enabled:
            return False

        table = self.rate_limit_model.__table__
        engine = self.session.get_bind()
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)

        with engine.begin() as conn:
            conn.execute(table.insert().values(key=key, attempted_at=now))

        with engine.connect() as conn:
            count = conn.execute(
                select(func.count(table.c.id)).where(
                    table.c.key == key,
                    table.c.attempted_at >= cutoff,
                )
            ).scalar()

        return count > max_attempts

    def cleanup(self, older_than_seconds: int = 3600) -> int:
        """Delete rate-limit entries older than *older_than_seconds*."""
        if not self.enabled:
            return 0

        table = self.rate_limit_model.__table__
        cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
        engine = self.session.get_bind()
        with engine.begin() as conn:
            result = conn.execute(
                table.delete().where(table.c.attempted_at < cutoff)
            )
            return result.rowcount
