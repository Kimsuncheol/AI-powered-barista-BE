from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel


class SummaryMetrics(BaseModel):
    totalOrders: int
    totalRevenue: Decimal
    totalCustomers: int
    todayOrders: int
    todayRevenue: Decimal


class TopItem(BaseModel):
    menuItemId: int
    name: str
    totalQuantity: int
    totalRevenue: Decimal


class RevenuePoint(BaseModel):
    date: date
    revenue: Decimal


class AnalyticsSummaryResponse(BaseModel):
    summary: SummaryMetrics


class AnalyticsTopItemsResponse(BaseModel):
    items: List[TopItem]


class AnalyticsRevenueResponse(BaseModel):
    points: List[RevenuePoint]
