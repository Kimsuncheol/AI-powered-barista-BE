"""Service orchestration for the floating AI chatbot."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.ai_interaction_log import AIInteractionLog, AIInteractionSource
from app.models.menu import MenuItem
from app.schemas.ai_chatbot import ChatbotRequest, ChatbotResponse, CoffeeRecommendationOut
from app.schemas.cart import CartItemCreate
from app.services.ai_chatbot_chain import ChatbotAIResult, run_chatbot_chain
from app.services.cart_service import add_item_to_cart
from app.services.user_service import get_user_by_id

logger = logging.getLogger(__name__)


class InvalidCoffeeRecommendationError(Exception):
    """Raised when AI suggestions reference invalid menu items."""


def _validate_and_enrich_recommendations(
    db: Session,
    recs: List[CoffeeRecommendationOut],
) -> List[CoffeeRecommendationOut]:
    """
    Validate AI recommendations against live menu data.

    Ensures each menu item exists, is available, and enforces authoritative
    price/description metadata from the database before returning to clients.
    """

    if not recs:
        return []

    ids = [rec.menuItemId for rec in recs]
    items = db.query(MenuItem).filter(MenuItem.id.in_(ids)).all()
    item_map = {item.id: item for item in items}
    validated: List[CoffeeRecommendationOut] = []

    for rec in recs:
        item = item_map.get(rec.menuItemId)
        if not item:
            raise InvalidCoffeeRecommendationError(f"Menu item {rec.menuItemId} not found")
        if not item.is_available:
            raise InvalidCoffeeRecommendationError(f"Menu item {rec.menuItemId} not available")

        server_price = float(item.price)

        validated.append(
            CoffeeRecommendationOut(
                menuItemId=item.id,
                name=item.name,
                description=rec.description or item.description or "",
                imageUrl=item.image_url,
                price=server_price,
                defaultQuantity=rec.defaultQuantity or 1,
            )
        )

    return validated


def _maybe_add_to_cart_from_recommendations(
    db: Session,
    user_id: Optional[int],
    recs: List[CoffeeRecommendationOut],
    accept_suggestion: bool,
) -> None:
    """
    If the user explicitly accepts the ADD_TO_CART flow, persist the first suggested item.
    """

    if not accept_suggestion or not user_id or not recs:
        return

    first = recs[0]
    payload = CartItemCreate(
        menu_item_id=first.menuItemId,
        quantity=first.defaultQuantity or 1,
    )
    add_item_to_cart(db=db, user_id=user_id, item_in=payload)


def handle_chatbot_request(db: Session, req: ChatbotRequest) -> ChatbotResponse:
    """
    Orchestrate floating chatbot behavior from LangChain output to persistence/logging.
    """

    if req.userId is not None:
        user = get_user_by_id(db, req.userId)
        if not user:
            raise ValueError("User not found")

    try:
        ai_result: ChatbotAIResult = run_chatbot_chain(
            user_message=req.userMessage,
            conversation_id=req.conversationId,
            user_id=req.userId,
            source=req.source,
        )

        raw_recs = [
            CoffeeRecommendationOut(
                menuItemId=rec.menuItemId,
                name=rec.name,
                description=rec.description,
                imageUrl=rec.imageUrl,
                price=rec.price,
                defaultQuantity=rec.defaultQuantity,
            )
            for rec in ai_result.coffeeRecommendations
        ]

        validated_recs = _validate_and_enrich_recommendations(db, raw_recs)

        if ai_result.action == "ADD_TO_CART":
            _maybe_add_to_cart_from_recommendations(
                db=db,
                user_id=req.userId,
                recs=validated_recs,
                accept_suggestion=bool(req.acceptSuggestion),
            )

        response = ChatbotResponse(
            replyText=ai_result.replyText,
            action=ai_result.action,
            coffeeRecommendations=validated_recs,
            conversationId=req.conversationId,
        )
    except InvalidCoffeeRecommendationError as exc:
        logger.warning("Invalid coffee recommendation: %s", exc)
        db.rollback()
        response = ChatbotResponse(
            replyText="I found something odd in my suggestions. You can still browse the menu manually!",
            action="NONE",
            coffeeRecommendations=[],
            conversationId=req.conversationId,
        )
    except Exception as exc:  # pragma: no cover - defensive reliability fallback
        logger.exception("Error in chatbot pipeline: %s", exc)
        db.rollback()
        response = ChatbotResponse(
            replyText="I’m having trouble thinking right now, but you can still browse the menu manually!",
            action="NONE",
            coffeeRecommendations=[],
            conversationId=req.conversationId,
        )

    raw_payload = response.model_dump() if hasattr(response, "model_dump") else response.dict()

    log = AIInteractionLog(
        user_id=req.userId,
        order_id=None,
        conversation_id=req.conversationId,
        source=AIInteractionSource.FLOATING_CHATBOT,
        user_message=req.userMessage,
        ai_reply=response.replyText,
        ai_action=response.action,
        raw_ai_payload=raw_payload,
    )
    db.add(log)
    db.commit()

    return response
