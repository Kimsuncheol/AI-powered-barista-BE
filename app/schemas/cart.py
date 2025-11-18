"""Pydantic schemas for cart endpoints."""

from typing import List, Optional

from pydantic import BaseModel


class CartItemBase(BaseModel):
    menu_item_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    """Payload for adding items to the cart."""

    pass


class CartItemUpdate(BaseModel):
    """Fields that can be patched on a cart line."""

    quantity: Optional[int] = None


class CartItemOut(BaseModel):
    id: int
    menu_item_id: int
    quantity: int

    class Config:
        orm_mode = True


class CartOut(BaseModel):
    items: List[CartItemOut]
