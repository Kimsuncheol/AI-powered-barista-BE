"""AI related API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_current_active_user_optional,
    get_db,
)
from app.models.user import User
from app.schemas.ai_assistant import (
    AIOrderAssistantRequest,
    AIOrderAssistantResponse,
)
from app.schemas.ai_chatbot import ChatbotRequest, ChatbotResponse
from app.services.ai_assistant_service import (
    InvalidAISuggestionError,
    run_ai_order_assistant,
)
from app.services.ai_chatbot_service import handle_chatbot_request

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/order-assistant", response_model=AIOrderAssistantResponse)
def ai_order_assistant(
    req: AIOrderAssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIOrderAssistantResponse:
    """Invoke the AI ordering assistant and optionally update the cart."""

    resolved_user_id = req.userId or current_user.id

    try:
        result = run_ai_order_assistant(db, req, resolved_user_id=resolved_user_id)
    except InvalidAISuggestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        # TODO: replace with structured logging (e.g. Sentry) instead of swallowing errors.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI assistant failed to process the request.",
        ) from exc

    return AIOrderAssistantResponse(
        replyText=result.replyText,
        action=result.action,
        suggestedItems=result.suggestedItems,
        conversationId=req.conversationId,
    )


@router.post("/chatbot", response_model=ChatbotResponse)
def chatbot_endpoint(
    body: ChatbotRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user_optional),
) -> ChatbotResponse:
    """
    Floating chatbot endpoint (FR-BE-23) handling conversational coffee assistance.
    """

    if current_user is not None:
        body.userId = current_user.id

    try:
        return handle_chatbot_request(db, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
