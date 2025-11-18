"""Service helpers for cart related operations."""

from typing import List

from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.schemas.ai_assistant import AISuggestedItem


def add_items_to_cart(db: Session, user_id: int, suggestions: List[AISuggestedItem]) -> None:
    """Persist AI suggested menu items into the user's cart."""

    if not suggestions:
        return

    for suggestion in suggestions:
        cart_item = CartItem(
            user_id=user_id,
            menu_item_id=suggestion.menuItemId,
            quantity=suggestion.quantity,
            # TODO: persist selectedOptions once cart schema supports it.
        )
        db.add(cart_item)

    db.commit()
