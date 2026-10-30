"""Sessions router — session management endpoints.

GET /sessions
DELETE /sessions/{id}
DELETE /sessions
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import MessageResponse, SessionListResponse
from src.application.services.authorization_service import require_authentication
from src.application.services.session_service import SessionService
from src.infrastructure.database.engine import get_db_session

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _get_session_service(db: AsyncSession = Depends(get_db_session)) -> SessionService:
    return SessionService(db)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    http_request: Request,
    user: dict = Depends(require_authentication),
    session_service: SessionService = Depends(_get_session_service),
):
    """List all active sessions for the current user."""
    current_jti = user.get("jti", "")
    return await session_service.list_sessions(UUID(user["id"]), current_jti=current_jti)


@router.delete("/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    user: dict = Depends(require_authentication),
    session_service: SessionService = Depends(_get_session_service),
):
    """Revoke a specific session."""
    await session_service.revoke_session(UUID(user["id"]), session_id)
    await session_service._session.commit()
    return MessageResponse(message="Session revoked successfully.")


@router.delete("", response_model=MessageResponse)
async def revoke_all_sessions(
    user: dict = Depends(require_authentication),
    session_service: SessionService = Depends(_get_session_service),
):
    """Revoke all sessions for the current user."""
    count = await session_service.revoke_all_sessions(UUID(user["id"]))
    await session_service._session.commit()
    return MessageResponse(message=f"Revoked {count} session(s).")
