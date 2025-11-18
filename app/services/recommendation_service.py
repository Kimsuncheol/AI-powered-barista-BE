"""Recommendation engine orchestration using LangChain."""

from typing import List, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.models.order import Order
from app.models.preference import Preference
from app.models.user import User
from app.schemas.recommendation import (
    AIRecommendationResult,
    RecommendationItem,
    RecommendationsResponse,
)
from app.services.menu_service import list_visible_menu_items
from app.services.user_service import get_or_create_preferences, list_user_orders


class RecommendationAIError(Exception):
    """Generic error when AI scoring fails."""


class InvalidAIRecommendationError(Exception):
    """Raised when AI recommendations fail validation."""


llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
)

parser = PydanticOutputParser(pydantic_object=AIRecommendationResult)

SYSTEM_PROMPT = """
You are a recommendation engine for a coffee shop.

Given:
- The user's preferences and order history.
- The list of currently available menu items.

You must output a JSON object with this exact schema:
{
  "items": [
    {
      "itemId": integer,
      "score": float,
      "reason": string
    }
  ]
}

Rules:
- Only recommend items whose IDs appear in the MENU ITEMS context.
- Use scores between 0.0 and 1.0. Higher is more relevant.
- You may return up to 10 items; fewer is fine if appropriate.
- For users with no history, recommend popular or seasonal-friendly items with generic reasons.
- Be consistent: if you infer user likes iced sweet coffee, recommend similar items.
- In "reason", refer to preferences or history if possible.
- Do NOT add any fields other than 'items', 'itemId', 'score', 'reason'.
""".strip()

USER_PROMPT_TEMPLATE = """
USER CONTEXT:
{user_context}

ORDER HISTORY SUMMARY:
{order_history_summary}

PREFERENCES SUMMARY:
{preferences_summary}

MENU ITEMS (AVAILABLE NOW):
{menu_context}

FORMAT INSTRUCTIONS:
{format_instructions}

Your task: Return a JSON object following the schema, with recommended items for this user.
""".strip()


def _get_user_context(db: Session, user: User) -> Tuple[List[Order], Preference]:
    """Collect order history and preferences for the user."""

    orders = list_user_orders(db, user.id)
    preferences = get_or_create_preferences(db, user.id)
    return orders, preferences


def _summarize_order_history(orders: List[Order]) -> str:
    """Return a lightweight textual summary of order history."""

    if not orders:
        return "User has no order history yet."

    lines = [f"Total orders: {len(orders)}."]
    # TODO: Enhance with iced vs hot trends, sweetness preferences, caffeine intensity, etc.
    return "\n".join(lines)


def _summarize_preferences(preference: Preference) -> str:
    """Convert preference fields into a concise text summary."""

    parts: List[str] = []
    if preference.favorite_drinks:
        parts.append(f"Favorite drink IDs: {preference.favorite_drinks}.")
    if preference.default_size:
        parts.append(f"Default size: {preference.default_size}.")
    if preference.default_milk_type:
        parts.append(f"Default milk type: {preference.default_milk_type}.")
    if preference.default_sugar_level:
        parts.append(f"Default sugar level: {preference.default_sugar_level}.")
    if not parts:
        return "User has no explicit saved preferences."
    # TODO: Expand to cover preferences like temperature, caffeine tolerance, etc.
    return " ".join(parts)


def _build_menu_context(items: List[MenuItem]) -> str:
    """Summarize visible menu items for the LLM."""

    if not items:
        return "No available menu items."

    lines: List[str] = []
    for item in items:
        tags = ", ".join(item.tags or [])
        category = item.category.value if hasattr(item.category, "value") else item.category
        lines.append(
            f"- ID: {item.id}, Name: {item.name}, Category: {category}, Price: {item.price}, Tags: [{tags}]"
        )
    return "\n".join(lines)


def _validate_and_clip_recommendations(
    ai_result: AIRecommendationResult,
    menu_items: List[MenuItem],
    limit: int,
) -> List[RecommendationItem]:
    """Ensure recommendations reference visible menu items and clamp scores."""

    items_by_id = {item.id: item for item in menu_items}
    cleaned: List[RecommendationItem] = []

    for rec in ai_result.items:
        if rec.itemId not in items_by_id:
            # Skip invalid items; alternatively we could raise to signal AI drift.
            continue

        if not 0.0 <= rec.score <= 1.0:
            # Clamp score between 0 and 1 as a guardrail.
            score = max(0.0, min(1.0, rec.score))
        else:
            score = rec.score

        cleaned.append(
            RecommendationItem(
                itemId=rec.itemId,
                score=score,
                reason=rec.reason,
            )
        )

    if not cleaned:
        raise InvalidAIRecommendationError("AI returned no valid menu recommendations.")

    cleaned.sort(key=lambda item: item.score, reverse=True)
    return cleaned[:limit]


def get_recommendations_for_user(
    db: Session,
    user: User,
    limit: int = 5,
) -> RecommendationsResponse:
    """Generate personalized menu recommendations for the user."""

    orders, preference = _get_user_context(db, user)
    menu_items = list_visible_menu_items(db)
    if not menu_items:
        # TODO: Provide fallback heuristics when menu catalog is empty or offline.
        return RecommendationsResponse(items=[])

    order_history_summary = _summarize_order_history(orders)
    preferences_summary = _summarize_preferences(preference)
    menu_context = _build_menu_context(menu_items)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT_TEMPLATE),
        ]
    )
    chain = prompt | llm | parser

    try:
        ai_result: AIRecommendationResult = chain.invoke(
            {
                "user_context": f"User ID: {user.id}, Email: {user.email}",
                "order_history_summary": order_history_summary,
                "preferences_summary": preferences_summary,
                "menu_context": menu_context,
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        # TODO: Log exception details (Sentry, OpenTelemetry) and consider caching fallback recommendations.
        raise RecommendationAIError("AI recommendation generation failed.") from exc

    validated_items = _validate_and_clip_recommendations(ai_result, menu_items, limit)
    return RecommendationsResponse(items=validated_items)


# TODO: Cache recommendations per user to avoid repeated LLM calls when preferences/history unchanged.
# TODO: Provide deterministic fallback recommendations when AI is unavailable.
# TODO: Unit tests to cover history vs. no-history users, invalid AI IDs, and score clamping/sorting behavior.
