"""Routes for recommendation related AI endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.schemas.recommendation import RecommendationsResponse
from app.services.recommendation_service import (
    InvalidAIRecommendationError,
    RecommendationAIError,
    get_recommendations_for_user,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> RecommendationsResponse:
    """Return personalized menu recommendations for the authenticated user."""

    try:
        return get_recommendations_for_user(db, current_user, limit=limit)
    except RecommendationAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations.",
        ) from exc
    except InvalidAIRecommendationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
