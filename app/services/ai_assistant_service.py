"""Service orchestration for the AI ordering assistant."""

import logging
from typing import List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.schemas.ai_assistant import AIOrderAssistantRequest, AIOrderAssistantResult
from app.services.cart_service import add_items_to_cart
from app.services.menu_service import list_visible_menu_items


logger = logging.getLogger(__name__)


class InvalidAISuggestionError(Exception):
    """Raised when AI suggestion refers to invalid menu IDs or option selections."""


llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
)

parser = PydanticOutputParser(pydantic_object=AIOrderAssistantResult)

SYSTEM_PROMPT = """
You are an AI ordering assistant for a coffee shop.

You MUST always respond with valid JSON only, matching this schema:
- replyText: string (natural language message for the user)
- action: one of ["NONE", "SUGGEST_ITEMS", "ADD_TO_CART"]
- suggestedItems: array of:
  - menuItemId: integer (ID from the menu context only)
  - quantity: integer (>=1)
  - selectedOptions: array of:
    - optionGroupId: integer
    - optionItemIds: array of integers

Semantics:
- "NONE": You are just chatting, no concrete menu suggestions needed.
- "SUGGEST_ITEMS": You suggest drinks/food but the user has NOT clearly accepted adding to cart yet.
- "ADD_TO_CART": The user has clearly accepted your suggestion and wants to proceed to add items to the cart.

Rules:
- Only use menuItemId values that appear in the provided MENU CONTEXT.
- For optionGroupId and optionItemIds, you must choose valid IDs that belong to the corresponding menu item.
- Be conservative: if you are unsure about user acceptance, use "SUGGEST_ITEMS" rather than "ADD_TO_CART".
- In replyText, keep it short and friendly, and explain what you're suggesting.
- Do NOT include any keys outside the specified JSON schema.
""".strip()

USER_PROMPT_TEMPLATE = """
MENU CONTEXT:
{menu_context}

CONVERSATION CONTEXT (optional):
{conversation_context}

USER MESSAGE:
{user_message}

Now produce a JSON object matching the required schema.
{format_instructions}
""".strip()


def _build_menu_context(items: List[MenuItem]) -> str:
    """Render menu items into a compact textual payload for the LLM."""

    lines: List[str] = []
    for item in items:
        option_groups = []
        for group in item.option_groups:
            option_names = ", ".join(f"{opt.id}:{opt.name}" for opt in group.options)
            option_groups.append(
                f"Group {group.id} ({group.name}, min {group.min_select}, max {group.max_select}): {option_names or 'No options'}"
            )
        option_summary = " | ".join(option_groups) if option_groups else "No options"
        lines.append(
            f"- ID: {item.id}, Name: {item.name}, Category: {item.category.value if hasattr(item.category, 'value') else item.category}, "
            f"Price: {item.price}, Options: {option_summary}"
        )
    return "\n".join(lines)


def _get_conversation_context(db: Session, conversation_id: Optional[str]) -> str:
    """Return stored conversation history (placeholder)."""

    # TODO: Persist and load AI conversation turns when conversationId is provided.
    return ""


def _validate_ai_suggestions(result: AIOrderAssistantResult, visible_items: List[MenuItem]) -> None:
    """Ensure AI returned only valid menu and option IDs."""

    if not result.suggestedItems:
        return

    items_by_id = {item.id: item for item in visible_items}

    for suggestion in result.suggestedItems:
        item = items_by_id.get(suggestion.menuItemId)
        if not item:
            raise InvalidAISuggestionError(
                f"Invalid menuItemId {suggestion.menuItemId} suggested by AI."
            )
        if suggestion.quantity < 1:
            raise InvalidAISuggestionError(
                f"Invalid quantity {suggestion.quantity} for item {suggestion.menuItemId}."
            )

        group_by_id = {group.id: group for group in item.option_groups}

        for selection in suggestion.selectedOptions:
            group = group_by_id.get(selection.optionGroupId)
            if not group:
                raise InvalidAISuggestionError(
                    f"Invalid optionGroupId {selection.optionGroupId} for menuItemId {suggestion.menuItemId}."
                )

            option_ids = {option.id for option in group.options}
            if len(selection.optionItemIds) < group.min_select or len(selection.optionItemIds) > group.max_select:
                raise InvalidAISuggestionError(
                    f"Option selection count {len(selection.optionItemIds)} violates min/max rules for group {group.id}."
                )

            for option_id in selection.optionItemIds:
                if option_id not in option_ids:
                    raise InvalidAISuggestionError(
                        f"Invalid optionItemId {option_id} for group {group.id}."
                    )


def _fallback_assistant_response() -> AIOrderAssistantResult:
    """Return a safe fallback when AI is unavailable (# RELIABILITY)."""

    return AIOrderAssistantResult(
        action="NONE",
        replyText="AI is temporarily unavailable. Please continue ordering manually.",
        suggestedItems=[],
    )


def run_ai_order_assistant(
    db: Session,
    req: AIOrderAssistantRequest,
    resolved_user_id: Optional[int] = None,
) -> AIOrderAssistantResult:
    """Execute the AI ordering flow end-to-end."""

    visible_items = list_visible_menu_items(db)
    menu_context = _build_menu_context(visible_items)
    conversation_context = _get_conversation_context(db, req.conversationId)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT_TEMPLATE),
        ]
    )
    chain = prompt | llm | parser

    try:
        result: AIOrderAssistantResult = chain.invoke(
            {
                "menu_context": menu_context,
                "conversation_context": conversation_context or "(no prior context)",
                "user_message": req.userMessage,
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("AI assistant call failed: %s", exc)
        # RELIABILITY: AI failure → fallback to manual guidance.
        return _fallback_assistant_response()

    try:
        _validate_ai_suggestions(result, visible_items)
    except InvalidAISuggestionError as exc:
        logger.warning("Invalid AI suggestion: %s", exc)
        return _fallback_assistant_response()

    if result.action == "ADD_TO_CART" and resolved_user_id is not None:
        add_items_to_cart(db, user_id=resolved_user_id, suggestions=result.suggestedItems)
    elif result.action == "ADD_TO_CART" and resolved_user_id is None:
        # TODO: add structured logging for auditing.
        pass

    # TODO: Persist conversation turn when conversationId provided.
    return result
