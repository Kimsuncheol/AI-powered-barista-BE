"""Cart CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.schemas.cart import CartItemCreate, CartItemOut, CartItemUpdate, CartOut
from app.services.cart_service import (
    CartItemNotFoundError,
    add_item_to_cart,
    get_cart_items_for_user,
    remove_cart_item,
    update_cart_item,
)

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> CartOut:
    """Return the authenticated user's cart contents."""

    items = get_cart_items_for_user(db, current_user.id)
    return CartOut(items=items)


@router.post("", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    item_in: CartItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> CartItemOut:
    """Add a new item or increment an existing line in the cart."""

    try:
        return add_item_to_cart(db, current_user.id, item_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{item_id}", response_model=CartItemOut)
def update_cart_item_endpoint(
    item_id: int,
    item_in: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> CartItemOut:
    """Update the quantity for a cart line."""

    try:
        return update_cart_item(db, current_user.id, item_id, item_in)
    except CartItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> None:
    """Remove a cart line for the user."""

    try:
        remove_cart_item(db, current_user.id, item_id)
    except CartItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return None
