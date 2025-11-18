from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.schemas.admin_user import AdminUserUpdate


class AdminUserNotFoundError(Exception):
    """Raised when an admin tries to manage a missing user."""


# TODO: add unit tests for admin user service behaviors.
def list_users(
    db: Session,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[User]:
    """Return users filtered by role, activity, and a lightweight search."""

    normalized_limit = max(1, min(limit, 50))
    query = db.query(User)
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        like = f"%{search}%"
        query = query.filter((User.email.ilike(like)) | (User.name.ilike(like)))

    return (
        query.order_by(User.created_at.desc())
        .offset(max(0, offset))
        .limit(normalized_limit)
        .all()
    )


def admin_update_user(
    db: Session,
    user_id: int,
    updates: AdminUserUpdate,
) -> User:
    """Update the role and/or activation flag for a user."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AdminUserNotFoundError("User not found")

    if updates.role is not None:
        user.role = updates.role
    if updates.is_active is not None:
        user.is_active = updates.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
