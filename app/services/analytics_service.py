from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.schemas.admin_analytics import RevenuePoint, SummaryMetrics, TopItem


# TODO: add unit tests for analytics queries and edge cases.
def get_summary_metrics(db: Session) -> SummaryMetrics:
    """Compute aggregate metrics for admin dashboards."""

    completed_statuses = [OrderStatus.ACCEPTED, OrderStatus.COMPLETED]

    total_orders = (
        db.query(func.count(Order.id)).filter(Order.status.in_(completed_statuses)).scalar() or 0
    )
    total_revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status.in_(completed_statuses))
        .scalar()
        or 0
    )
    total_customers = db.query(func.count(User.id)).scalar() or 0

    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = datetime.combine(tomorrow, datetime.min.time())

    today_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.status.in_(completed_statuses),
            Order.created_at >= today_start,
            Order.created_at < tomorrow_start,
        )
        .scalar()
        or 0
    )
    today_revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.status.in_(completed_statuses),
            Order.created_at >= today_start,
            Order.created_at < tomorrow_start,
        )
        .scalar()
        or 0
    )

    # TODO: cache summary metrics in Redis/memory for a short TTL to avoid repeated scans.
    return SummaryMetrics(
        totalOrders=total_orders,
        totalRevenue=Decimal(str(total_revenue)),
        totalCustomers=total_customers,
        todayOrders=today_orders,
        todayRevenue=Decimal(str(today_revenue)),
    )


def get_top_items(db: Session, limit: int = 10) -> List[TopItem]:
    """Return the top selling menu items."""

    rows = (
        db.query(
            OrderItem.menu_item_id,
            func.sum(OrderItem.quantity).label("qty"),
            func.sum(OrderItem.line_total).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.COMPLETED]))
        .group_by(OrderItem.menu_item_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )

    menu_items = {
        m.id: m
        for m in db.query(MenuItem)
        .filter(MenuItem.id.in_([row.menu_item_id for row in rows]))
        .all()
    }

    result: List[TopItem] = []
    for row in rows:
        menu_item = menu_items.get(row.menu_item_id)
        result.append(
            TopItem(
                menuItemId=row.menu_item_id,
                name=menu_item.name if menu_item else f"Item {row.menu_item_id}",
                totalQuantity=int(row.qty or 0),
                totalRevenue=Decimal(str(row.revenue or 0)),
            )
        )
    return result


def get_revenue_timeseries(db: Session, days: int = 30) -> List[RevenuePoint]:
    """Return revenue aggregated per day for the requested window."""

    completed_statuses = [OrderStatus.ACCEPTED, OrderStatus.COMPLETED]
    start_date = date.today() - timedelta(days=days - 1)
    start_datetime = datetime.combine(start_date, datetime.min.time())

    rows = (
        db.query(
            func.date(Order.created_at).label("d"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .filter(
            Order.status.in_(completed_statuses),
            Order.created_at >= start_datetime,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    by_date = {row.d: row.revenue for row in rows}

    points: List[RevenuePoint] = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        revenue = Decimal(str(by_date.get(day, 0)))
        points.append(RevenuePoint(date=day, revenue=revenue))

    # TODO: allow advanced date filtering and grouping (weeks/months).
    return points
