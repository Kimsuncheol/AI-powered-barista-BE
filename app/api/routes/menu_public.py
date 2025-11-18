from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.menu import MenuItemOut
from app.services.menu_service import list_visible_menu_items

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/items", response_model=List[MenuItemOut])
def get_visible_menu_items(db: Session = Depends(get_db)) -> List[MenuItemOut]:
    return list_visible_menu_items(db)
