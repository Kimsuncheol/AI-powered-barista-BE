from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.schemas.admin_analytics import (
    AnalyticsRevenueResponse,
    AnalyticsSummaryResponse,
    AnalyticsTopItemsResponse,
)
from app.services.analytics_service import (
    get_revenue_timeseries,
    get_summary_metrics,
    get_top_items,
)

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def admin_analytics_summary(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
):
    summary = get_summary_metrics(db)
    return AnalyticsSummaryResponse(summary=summary)


@router.get("/top-items", response_model=AnalyticsTopItemsResponse)
def admin_analytics_top_items(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
    limit: int = Query(10, ge=1, le=50),
):
    items = get_top_items(db, limit=limit)
    return AnalyticsTopItemsResponse(items=items)


@router.get("/revenue", response_model=AnalyticsRevenueResponse)
def admin_analytics_revenue(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user),
    days: int = Query(30, ge=1, le=365),
):
    points = get_revenue_timeseries(db, days=days)
    # TODO: enforce stricter auth/auditing for analytics dashboards.
    return AnalyticsRevenueResponse(points=points)
