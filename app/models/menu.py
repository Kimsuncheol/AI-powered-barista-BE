from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MenuCategory(str, PyEnum):
    COFFEE = "COFFEE"
    TEA = "TEA"
    FRAPPE = "FRAPPE"
    DESSERT = "DESSERT"
    OTHER = "OTHER"


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(Enum(MenuCategory), nullable=False, default=MenuCategory.OTHER, index=True)
    tags = Column(JSON, nullable=True)
    is_seasonal = Column(Boolean, nullable=False, default=False)
    season_start = Column(Date, nullable=True)
    season_end = Column(Date, nullable=True)
    is_available = Column(Boolean, nullable=False, default=True, index=True)
    stock_quantity = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    option_groups = relationship(
        "OptionGroup",
        back_populates="menu_item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # TODO: add Alembic migration for menu_items along with option groups/items (including image_url and indexes).


class OptionGroup(Base):
    __tablename__ = "option_groups"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(
        Integer,
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    is_required = Column(Boolean, nullable=False, default=False)
    min_select = Column(Integer, nullable=False, default=0)
    max_select = Column(Integer, nullable=False, default=1)

    menu_item = relationship("MenuItem", back_populates="option_groups")
    options = relationship(
        "OptionItem",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OptionItem(Base):
    __tablename__ = "option_items"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("option_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    price_delta = Column(Numeric(10, 2), nullable=False, default=0)
    is_default = Column(Boolean, nullable=False, default=False)

    group = relationship("OptionGroup", back_populates="options")

    # TODO: add Alembic migration for option_groups and option_items.
