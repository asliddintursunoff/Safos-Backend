from django.urls import path

from apps.markets.api.analytics.views import (
    MarketActivityAnalyticsAPIView,
    MarketActivityBulkStatusAPIView,
    MarketAnalyticsDetailAPIView,
    MarketAnalyticsSummaryAPIView,
    MarketDebtOrderListAPIView,
    MarketStatusUpdateAPIView,
    MarketVolumeAnalyticsAPIView,
)
from .views import MarketListCreateAPIView, MarketRetrieveUpdateDestroyAPIView

urlpatterns = [
    path(
        "analytics/volume/",
        MarketVolumeAnalyticsAPIView.as_view(),
        name="market-analytics-volume",
    ),
    path(
        "analytics/activity/",
        MarketActivityAnalyticsAPIView.as_view(),
        name="market-analytics-activity",
    ),
    path(
        "analytics/activity/status/",
        MarketActivityBulkStatusAPIView.as_view(),
        name="market-analytics-bulk-status",
    ),
    path(
        "analytics/summary/",
        MarketAnalyticsSummaryAPIView.as_view(),
        name="market-analytics-summary",
    ),
    path(
        "analytics/<uuid:id>/debts/",
        MarketDebtOrderListAPIView.as_view(),
        name="market-analytics-debts",
    ),
    path(
        "analytics/<uuid:id>/status/",
        MarketStatusUpdateAPIView.as_view(),
        name="market-analytics-status",
    ),
    path(
        "analytics/<uuid:id>/",
        MarketAnalyticsDetailAPIView.as_view(),
        name="market-analytics-detail",
    ),
    path("", MarketListCreateAPIView.as_view(), name="market-list-create"),
    path(
        "<uuid:id>/",
        MarketRetrieveUpdateDestroyAPIView.as_view(),
        name="market-retrieve-update-destroy",
    ),
]