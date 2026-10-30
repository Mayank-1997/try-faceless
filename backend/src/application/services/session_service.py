"""Session service — active session management and revocation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import SessionListResponse, SessionResponse
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import SessionNotFoundError
from src.persistence.repositories.auth_repositories import SqlAlchemySessionRepository


class SessionService:
    """Service for user session management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logger = get_logger(__name__)
        self._repo = SqlAlchemySessionRepository(session)

    async def list_sessions(
        self,
        user_id: UUID,
        *,
        current_jti: str | None = None,
    ) -> SessionListResponse:
        """List all active sessions for a user.

        Args:
            user_id: The user's UUID.
            current_jti: JTI of the current session (to mark as current).

        Returns:
            ``SessionListResponse`` with all active sessions.
        """
        sessions = await self._repo.list_by_user(user_id, active_only=True)
        responses = [
            SessionResponse(
                id=s.id,
                device=s.device,
                browser=s.browser,
                operating_system=s.operating_system,
                ip_address=s.ip_address,
                status=s.status.value,
                created_at=s.created_at,
                last_activity_at=s.last_activity_at,
                expires_at=s.expires_at,
                is_current=(s.token_jti == current_jti) if current_jti else False,
            )
            for s in sessions
        ]
        return SessionListResponse(sessions=responses, total=len(responses))

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> bool:
        """Revoke a specific session.

        Raises:
            SessionNotFoundError: If the session doesn't exist or doesn't belong to the user.
        """
        session = await self._repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError()

        await self._repo.revoke(session_id)
        self._logger.info("session_revoked", user_id=str(user_id), session_id=str(session_id))
        return True

    async def revoke_all_sessions(self, user_id: UUID) -> int:
        """Revoke all active sessions for a user.

        Returns:
            Number of sessions revoked.
        """
        count = await self._repo.revoke_all_for_user(user_id)
        self._logger.info("all_sessions_revoked", user_id=str(user_id), count=count)
        return count
