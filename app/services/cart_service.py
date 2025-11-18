"""Service helpers for cart related operations."""

from typing import List

from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.schemas.ai_assistant import AISuggestedItem
from app.schemas.cart import CartItemCreate, CartItemUpdate


class CartItemNotFoundError(Exception):
    """Raised when a requested cart line is missing."""


def get_cart_items_for_user(db: Session, user_id: int) -> List[CartItem]:
    """Return all cart lines for the user."""

    return db.query(CartItem).filter(CartItem.user_id == user_id).all()


def add_item_to_cart(db: Session, user_id: int, item_in: CartItemCreate) -> CartItem:
    """Add or increment a cart line for the user."""

    if item_in.quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    existing = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user_id,
            CartItem.menu_item_id == item_in.menu_item_id,
        )
        .first()
    )

    if existing:
        existing.quantity += item_in.quantity
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    cart_item = CartItem(
        user_id=user_id,
        menu_item_id=item_in.menu_item_id,
        quantity=item_in.quantity,
        # TODO: persist selected options once cart schema supports it.
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


def update_cart_item(db: Session, user_id: int, item_id: int, item_in: CartItemUpdate) -> CartItem:
    """Update a cart line quantity or delete if the new quantity is <= 0."""

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.id == item_id)
        .first()
    )
    if not cart_item:
        raise CartItemNotFoundError("Cart item not found")

    if item_in.quantity is not None:
        if item_in.quantity <= 0:
            db.delete(cart_item)
            db.commit()
            return cart_item
        cart_item.quantity = item_in.quantity

    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


def remove_cart_item(db: Session, user_id: int, item_id: int) -> None:
    """Remove a cart line entirely."""

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.id == item_id)
        .first()
    )
    if not cart_item:
        raise CartItemNotFoundError("Cart item not found")
    db.delete(cart_item)
    db.commit()


def clear_cart(db: Session, user_id: int) -> None:
    """Delete all cart lines for the user."""

    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()


def add_items_to_cart(db: Session, user_id: int, suggestions: List[AISuggestedItem]) -> None:
    """Persist AI suggested menu items into the user's cart."""

    if not suggestions:
        return

    for suggestion in suggestions:
        payload = CartItemCreate(
            menu_item_id=suggestion.menuItemId,
            quantity=suggestion.quantity,
        )
        add_item_to_cart(db, user_id, payload)
