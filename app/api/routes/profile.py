from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.order import OrderSummary
from app.schemas.preference import PreferencesOut
from app.schemas.user import UserOut, UserUpdate
from app.services.order_service import list_orders_for_user
from app.services.preference_service import get_preferences_for_user
from app.services.user_service import update_user_profile

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_active_user)) -> UserOut:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserOut:
    return update_user_profile(db, current_user, user_update)


@router.get("/me/orders", response_model=List[OrderSummary])
def read_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrderSummary]:
    return list_orders_for_user(db, current_user.id)


@router.get("/me/preferences", response_model=PreferencesOut)
def read_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PreferencesOut:
    return get_preferences_for_user(db, current_user.id)
