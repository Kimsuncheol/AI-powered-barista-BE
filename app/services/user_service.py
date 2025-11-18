from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import RoleUpdate, UserUpdate


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def update_user_profile(db: Session, user: User, user_in: UserUpdate) -> User:
    if user_in.name is not None:
        user.name = user_in.name
    if user_in.phone is not None:
        user.phone = user_in.phone
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_role(db: Session, user: User, role_in: RoleUpdate) -> User:
    user.role = role_in.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
