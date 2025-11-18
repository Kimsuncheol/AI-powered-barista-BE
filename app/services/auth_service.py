from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.user_service import get_user_by_email


class EmailAlreadyRegisteredError(Exception):
    """Raised when a registration attempt uses an existing email."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


def register_user(db: Session, user_in: UserCreate) -> User:
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise EmailAlreadyRegisteredError("Email already registered")

    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        name=user_in.name,
        phone=user_in.phone,
        hashed_password=hashed_password,
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")
    if not user.is_active:
        raise InvalidCredentialsError("Inactive user")
    return user


def create_access_token_for_user(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
    }
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(payload, expires_delta=expires)
