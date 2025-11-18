"""Schemas for the floating AI chatbot."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatbotRequest(BaseModel):
    userMessage: str = Field(..., min_length=1)
    conversationId: str
    userId: Optional[int] = None
    source: Literal["FLOATING_CHATBOT"] = "FLOATING_CHATBOT"
    acceptSuggestion: Optional[bool] = False


class CoffeeRecommendationOut(BaseModel):
    menuItemId: int
    name: str
    description: str
    imageUrl: Optional[str] = None
    price: float
    defaultQuantity: int = 1


class ChatbotResponse(BaseModel):
    replyText: str
    action: Literal["NONE", "SUGGEST_ITEMS", "ADD_TO_CART"]
    coffeeRecommendations: List[CoffeeRecommendationOut] = Field(default_factory=list)
    conversationId: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
