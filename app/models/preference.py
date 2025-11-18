from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    favorite_drinks = Column(JSON, nullable=True, default=list)
    default_size = Column(String(50), nullable=True)
    default_milk_type = Column(String(50), nullable=True)
    default_sugar_level = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", backref="preferences")

    # TODO: normalize favorite drinks into a join table if the catalog grows.
    # TODO: add an Alembic migration for preferences alongside orders and users.
