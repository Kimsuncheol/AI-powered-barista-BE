"""Schemas for the AI ordering assistant."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AIOrderAssistantRequest(BaseModel):
    """Request body for the AI ordering assistant endpoint."""

    userMessage: str
    conversationId: Optional[str] = None
    userId: Optional[int] = None


class AISuggestedOptionSelection(BaseModel):
    """Option selections suggested by the AI for a menu item."""

    optionGroupId: int
    optionItemIds: List[int]


class AISuggestedItem(BaseModel):
    """Menu item suggestion from the AI assistant."""

    menuItemId: int
    quantity: int
    selectedOptions: List[AISuggestedOptionSelection] = Field(default_factory=list)


class AIOrderAssistantResult(BaseModel):
    """Structured result expected from the AI model."""

    replyText: str
    action: Literal["NONE", "SUGGEST_ITEMS", "ADD_TO_CART"]
    suggestedItems: List[AISuggestedItem] = Field(default_factory=list)


class AIOrderAssistantResponse(BaseModel):
    """Response returned by the AI ordering assistant endpoint."""

    replyText: str
    action: Literal["NONE", "SUGGEST_ITEMS", "ADD_TO_CART"]
    suggestedItems: List[AISuggestedItem] = Field(default_factory=list)
    conversationId: Optional[str] = None
