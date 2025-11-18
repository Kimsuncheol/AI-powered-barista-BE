"""Cart related database models."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.base import Base


class CartItem(Base):
    """Cart line items created when AI suggestions are accepted."""

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    # TODO: persist selected options via JSON or join table when cart UX is finalized.

    user = relationship("User")
    menu_item = relationship("MenuItem")
