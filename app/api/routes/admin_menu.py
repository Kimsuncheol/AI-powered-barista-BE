from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.schemas.admin_menu import MenuImageUploadResponse
from app.schemas.menu import MenuItemCreate, MenuItemOut, MenuItemUpdate
from app.services.admin_menu_service import attach_image_to_menu_item, upload_menu_image
from app.services.menu_service import (
    InvalidSeasonWindowError,
    MenuItemNotFoundError,
    create_menu_item,
    delete_menu_item,
    list_all_menu_items,
    update_menu_item,
)

router = APIRouter(prefix="/admin/menu", tags=["admin-menu"])


@router.get("/items", response_model=List[MenuItemOut])
def admin_list_menu_items(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> List[MenuItemOut]:
    # TODO: tighten admin authentication/authorization for menu management (auditing).
    return list_all_menu_items(db, limit=limit, offset=offset)


@router.post("/items", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def admin_create_menu_item(
    item_in: MenuItemCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
) -> MenuItemOut:
    try:
        return create_menu_item(db, item_in)
    except InvalidSeasonWindowError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/items/{item_id}", response_model=MenuItemOut)
def admin_update_menu_item(
    item_id: int,
    item_in: MenuItemUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
) -> MenuItemOut:
    try:
        return update_menu_item(db, item_id, item_in)
    except MenuItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidSeasonWindowError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
) -> None:
    try:
        delete_menu_item(db, item_id)
    except MenuItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/items/{item_id}/image", response_model=MenuImageUploadResponse)
def admin_upload_menu_item_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
) -> MenuImageUploadResponse:
    image_url = upload_menu_image(file)
    item = attach_image_to_menu_item(db, item_id, image_url)
    return MenuImageUploadResponse(imageUrl=item.image_url or image_url)
