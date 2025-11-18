from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.menu import MenuCategory


class OptionItemBase(BaseModel):
    name: str
    price_delta: Decimal = Decimal("0")
    is_default: bool = False


class OptionItemCreate(OptionItemBase):
    pass


class OptionItemUpdate(BaseModel):
    name: Optional[str] = None
    price_delta: Optional[Decimal] = None
    is_default: Optional[bool] = None


class OptionItemOut(OptionItemBase):
    id: int

    class Config:
        orm_mode = True


class OptionGroupBase(BaseModel):
    name: str
    is_required: bool = False
    min_select: int = 0
    max_select: int = 1


class OptionGroupCreate(OptionGroupBase):
    options: List[OptionItemCreate] = Field(default_factory=list)


class OptionGroupUpdate(BaseModel):
    name: Optional[str] = None
    is_required: Optional[bool] = None
    min_select: Optional[int] = None
    max_select: Optional[int] = None
    options: Optional[List[OptionItemCreate]] = None


class OptionGroupOut(OptionGroupBase):
    id: int
    options: List[OptionItemOut] = Field(default_factory=list)

    class Config:
        orm_mode = True


class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: MenuCategory
    tags: Optional[List[str]] = None
    is_seasonal: bool = False
    season_start: Optional[date] = None
    season_end: Optional[date] = None
    is_available: bool = True
    stock_quantity: Optional[int] = None


class MenuItemCreate(MenuItemBase):
    option_groups: List[OptionGroupCreate] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[MenuCategory] = None
    tags: Optional[List[str]] = None
    is_seasonal: Optional[bool] = None
    season_start: Optional[date] = None
    season_end: Optional[date] = None
    is_available: Optional[bool] = None
    stock_quantity: Optional[int] = None
    option_groups: Optional[List[OptionGroupCreate]] = None


class MenuItemOut(MenuItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    option_groups: List[OptionGroupOut] = Field(default_factory=list)

    class Config:
        orm_mode = True
