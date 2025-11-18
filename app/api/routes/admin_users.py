from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.models.user import UserRole
from app.schemas.admin_user import AdminUserOut, AdminUserUpdate
from app.services.admin_user_service import (
    AdminUserNotFoundError,
    admin_update_user,
    list_users,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[AdminUserOut])
def admin_list_users(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    # NFR-BE-1 Performance: paginate admin listing endpoints.
    return list_users(
        db,
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.patch("/{user_id}", response_model=AdminUserOut)
def admin_update_user_endpoint(
    user_id: int,
    updates: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
):
    try:
        return admin_update_user(db, user_id, updates)
    except AdminUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
