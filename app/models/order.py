from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OrderStatus(str, PyEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PREPARATION = "IN_PREPARATION"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    payment_provider = Column(String(50), nullable=True)
    payment_status = Column(String(50), nullable=True)
    paypal_order_id = Column(String(255), nullable=True)
    paypal_capture_id = Column(String(255), nullable=True)

    user = relationship("User")

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # TODO: add Alembic migration for orders/order_items/status_history tables and payment columns.


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(Enum(OrderStatus), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="status_history")
