from datetime import datetime, timezone
from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.services.user_service import get_user_by_id


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_token_from_headers(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    # TODO: tighten cookie settings (HttpOnly, secure, SameSite) when production ready.
    return request.cookies.get("access_token")


def _decode_jwt_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        exp = payload.get("exp")
        if sub is None:
            raise JWTError("Missing subject")
        if exp is None:
            raise JWTError("Missing exp claim")
        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise JWTError("Token expired")
        return int(sub)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _resolve_user(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _get_token_from_headers(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = _decode_jwt_token(token)
    return _resolve_user(db, user_id)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def get_current_active_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Resolve the current user if a valid token exists; otherwise return None.
    """

    token = _get_token_from_headers(request)
    if not token:
        return None
    user_id = _decode_jwt_token(token)
    user = _resolve_user(db, user_id)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_current_staff_or_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role not in (UserRole.STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or Admin privileges required",
        )
    return current_user


def get_current_user_from_token(token: str, db: Session) -> User:
    """Resolve a user from a raw JWT (used for WebSockets)."""

    user_id = _decode_jwt_token(token)
    return _resolve_user(db, user_id)
