from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.schemas.user import RoleUpdate, UserOut
from app.services.user_service import get_user_by_id, list_users, update_user_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=List[UserOut])
def read_users(
    _: object = Depends(get_current_admin_user), db: Session = Depends(get_db)
) -> List[UserOut]:
    return list_users(db)


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role_endpoint(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin_user),
) -> UserOut:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return update_user_role(db, user, payload)
