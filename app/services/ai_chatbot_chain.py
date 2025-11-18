"""LangChain pipeline powering the floating chatbot."""

from typing import List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings


class CoffeeRecommendation(BaseModel):
    menuItemId: int = Field(..., description="ID of the menu item (FK to menu_items.id)")
    name: str = Field(..., description="Display name of the drink")
    description: str = Field(..., description="Short description in natural language")
    imageUrl: Optional[str] = Field(
        default=None,
        description="Image URL if available; can be null",
    )
    price: float = Field(..., description="Base or combined price in store currency")
    defaultQuantity: int = Field(
        default=1,
        ge=1,
        description="Default quantity to show in UI; must be >= 1",
    )


class ChatbotAIResult(BaseModel):
    replyText: str = Field(..., description="Friendly barista-style textual reply to the user")
    action: Literal["NONE", "SUGGEST_ITEMS", "ADD_TO_CART"] = Field(
        ...,
        description=(
            "NONE: just answer; "
            "SUGGEST_ITEMS: recommend drinks; "
            "ADD_TO_CART: strong suggestion to add one of the recommended drinks to cart"
        ),
    )
    coffeeRecommendations: List[CoffeeRecommendation] = Field(
        default_factory=list,
        description="List of drink recommendations. Can be empty.",
    )


parser = PydanticOutputParser(pydantic_object=ChatbotAIResult)


def _get_llm() -> ChatOpenAI:
    """Return the configured LLM client."""

    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.5,
        openai_api_key=settings.OPENAI_API_KEY,
    )


BASE_SYSTEM_PROMPT = """
You are an AI barista for an online coffee shop.

Your goals:
- Answer coffee-related and menu-related questions in a friendly, concise tone.
- Suggest drinks only from the store's menu.
- Prefer iced sweet coffee when the user asks for something sweet or iced.
- Avoid recommending items that are described as unavailable, out of stock, or out of season in the context you receive.

CRITICAL:
- You MUST return your final answer ONLY in the JSON format specified below.
- Do not include any extra commentary outside JSON.
- Carefully follow the schema:
  - replyText: a short natural language response.
  - action: one of "NONE", "SUGGEST_ITEMS", "ADD_TO_CART".
  - coffeeRecommendations: a list that may be empty.

If the user is just chatting and no drink recommendation is needed:
- Use action "NONE" and an empty coffeeRecommendations list.

If you recommend drinks:
- Use action "SUGGEST_ITEMS" or "ADD_TO_CART".
- Each coffeeRecommendations item MUST include:
  - menuItemId (int)
  - name (str)
  - description (str)
  - imageUrl (string or null)
  - price (float)
  - defaultQuantity (int >= 1; default 1)

{format_instructions}
""".strip()


def _build_system_prompt() -> str:
    """Insert formatted schema instructions into the system prompt."""

    return BASE_SYSTEM_PROMPT.format(format_instructions=parser.get_format_instructions())


def run_chatbot_chain(
    user_message: str,
    conversation_id: str,
    user_id: Optional[int],
    source: str,
) -> ChatbotAIResult:
    """
    Run the LangChain-powered chatbot and return structured AI output.
    """

    llm = _get_llm()
    system_prompt = _build_system_prompt()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Conversation ID: {conversation_id}\n"
                f"User ID: {user_id}\n"
                f"Source: {source}\n\n"
                f"User message: {user_message}"
            )
        ),
    ]

    raw = llm.invoke(messages)

    try:
        result: ChatbotAIResult = parser.parse(raw.content)
    except Exception as exc:  # pragma: no cover - delegated to service fallback
        raise RuntimeError(f"Failed to parse chatbot output: {exc}") from exc

    return result


__all__ = ["ChatbotAIResult", "CoffeeRecommendation", "run_chatbot_chain"]
