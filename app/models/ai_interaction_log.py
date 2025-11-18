"""AI interaction logging model."""

from datetime import datetime
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
try:  # pragma: no cover - dialect-specific fallback
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:  # pragma: no cover
    from sqlalchemy import JSON as JSONB  # type: ignore
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIInteractionSource(str, enum.Enum):
    """Sources that can emit AI interactions."""

    ORDER_ASSISTANT = "ORDER_ASSISTANT"
    RECOMMENDATIONS = "RECOMMENDATIONS"
    FLOATING_CHATBOT = "FLOATING_CHATBOT"


class AIInteractionLog(Base):
    """Persisted log of AI ↔ user messages."""

    __tablename__ = "ai_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    conversation_id = Column(String(255), nullable=True, index=True)
    source = Column(Enum(AIInteractionSource), nullable=False)
    user_message = Column(Text, nullable=False)
    ai_reply = Column(Text, nullable=False)
    ai_action = Column(String(50), nullable=True)
    raw_ai_payload = Column(JSONB, nullable=True)  # Stores structured AI response bodies
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", backref="ai_interactions")
    order = relationship("Order", backref="ai_interactions")
