from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.menu import MenuItemOut
from app.services.menu_service import list_visible_menu_items

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/items", response_model=List[MenuItemOut])
def get_visible_menu_items(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> List[MenuItemOut]:
    # NFR-BE-1 Performance: paginate menu listings for lighter payloads.
    return list_visible_menu_items(db, limit=limit, offset=offset)
