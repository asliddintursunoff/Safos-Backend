from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.choices import MARKET_STATUS_CHOICES
from apps.markets.api.analytics.serializers import (
    AnalyticsSummarySerializer,
    BulkMarketStatusUpdateSerializer,
    MarketActivitySerializer,
    MarketAnalyticsDetailSerializer,
    MarketDebtOrderSerializer,
    MarketVolumeSerializer,
    SingleMarketStatusUpdateSerializer,
)
from apps.common.permissions import IsAdminOrDeliverer, IsAdminRole
from apps.markets.api.pagination import MarketAnalyticsPagination
from apps.markets.models import Market
from apps.markets.services.analytics import (
    ACTIVITY_ORDERING,
    VOLUME_ORDERING,
    annotate_market_analytics,
    apply_has_debt_filter,
    apply_inactive_days_filter,
    dashboard_summary,
    delivered_orders_with_remaining,
    parse_bool_param,
    parse_inactive_days,
    parse_optional_date_range,
    parse_ordering,
    update_market_statuses,
    volume_list_summary,
)

DATE_PARAMS = [
    OpenApiParameter(
        name="date",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Bitta kun. Format: dd-mm-yyyy. Faqat buyurtma summasi uchun. Qarzga ta'sir qilmaydi.",
        required=False,
    ),
    OpenApiParameter(
        name="start_date",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Oraliq boshi. Format: dd-mm-yyyy. Faqat buyurtma summasi uchun.",
        required=False,
    ),
    OpenApiParameter(
        name="end_date",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Oraliq oxiri. Format: dd-mm-yyyy. Faqat buyurtma summasi uchun.",
        required=False,
    ),
]

HAS_DEBT_PARAM = OpenApiParameter(
    name="has_debt",
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description="Joriy qarz bo'yicha filter. Sana oralig'iga bog'liq emas.",
    required=False,
)

STATUS_PARAM = OpenApiParameter(
    name="status",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Do'kon holati: " + ", ".join(MARKET_STATUS_CHOICES.keys()),
    required=False,
)

SEARCH_PARAM = OpenApiParameter(
    name="search",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Do'kon nomi bo'yicha qidiruv",
    required=False,
)


def _apply_status_filter(queryset, query_params):
    status = query_params.get("status")
    if not status:
        return queryset
    if status not in MARKET_STATUS_CHOICES:
        raise ValidationError(
            {
                "status": "Ruxsat etilgan qiymatlar: "
                + ", ".join(MARKET_STATUS_CHOICES.keys())
            }
        )
    return queryset.filter(statuses__status=status)


def _base_market_qs():
    return Market.objects.select_related("statuses", "owner")


@extend_schema(
    parameters=[
        *DATE_PARAMS,
        HAS_DEBT_PARAM,
        STATUS_PARAM,
        SEARCH_PARAM,
        OpenApiParameter(
            name="ordering",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Default: -ordered_amount (ko'pdan kam). "
                + ", ".join(sorted(VOLUME_ORDERING.keys()))
            ),
            required=False,
        ),
    ],
    responses={200: MarketVolumeSerializer(many=True)},
)
class MarketVolumeAnalyticsAPIView(ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = MarketVolumeSerializer
    pagination_class = MarketAnalyticsPagination
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        params = self.request.query_params
        self.date_from, self.date_to = parse_optional_date_range(params)
        queryset = annotate_market_analytics(
            _base_market_qs(),
            self.date_from,
            self.date_to,
        )
        queryset = apply_has_debt_filter(
            queryset, parse_bool_param(params, "has_debt")
        )
        queryset = _apply_status_filter(queryset, params)
        ordering = parse_ordering(params, VOLUME_ORDERING, "-ordered_amount")
        return queryset.order_by(ordering, "name")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        totals = volume_list_summary(queryset)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        response = self.get_paginated_response(serializer.data)
        response.data["summary"] = {
            **totals,
            "date_from": (
                self.date_from.strftime("%d-%m-%Y") if self.date_from else None
            ),
            "date_to": self.date_to.strftime("%d-%m-%Y") if self.date_to else None,
        }
        return response


@extend_schema(
    parameters=[
        HAS_DEBT_PARAM,
        STATUS_PARAM,
        SEARCH_PARAM,
        OpenApiParameter(
            name="inactive_days",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Shu kundan ko'p buyurtma olmagan do'konlar (masalan 7, 8, 30).",
            required=False,
        ),
        OpenApiParameter(
            name="ordering",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Default: -days_since_last_order. "
                + ", ".join(sorted(ACTIVITY_ORDERING.keys()))
            ),
            required=False,
        ),
    ],
    responses={200: MarketActivitySerializer(many=True)},
)
class MarketActivityAnalyticsAPIView(ListAPIView):
    permission_classes = [IsAdminOrDeliverer]
    serializer_class = MarketActivitySerializer
    pagination_class = MarketAnalyticsPagination
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        params = self.request.query_params
        queryset = annotate_market_analytics(_base_market_qs())
        queryset = apply_has_debt_filter(
            queryset, parse_bool_param(params, "has_debt")
        )
        queryset = apply_inactive_days_filter(
            queryset, parse_inactive_days(params)
        )
        queryset = _apply_status_filter(queryset, params)
        ordering = parse_ordering(
            params, ACTIVITY_ORDERING, "-days_since_last_order"
        )
        return queryset.order_by(ordering, "name")


@extend_schema(
    request=BulkMarketStatusUpdateSerializer,
    responses={200: OpenApiTypes.OBJECT},
)
class MarketActivityBulkStatusAPIView(APIView):
    permission_classes = [IsAdminRole]

    def put(self, request, *args, **kwargs):
        serializer = BulkMarketStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_ids, skipped = update_market_statuses(
            serializer.validated_data["market_ids"],
            serializer.validated_data["status"],
        )
        return Response(
            {
                "updated_count": len(updated_ids),
                "updated_ids": updated_ids,
                "skipped": skipped,
            }
        )


@extend_schema(responses={200: AnalyticsSummarySerializer})
class MarketAnalyticsSummaryAPIView(APIView):
    permission_classes = [IsAdminOrDeliverer]

    def get(self, request, *args, **kwargs):
        data = dashboard_summary()
        return Response(AnalyticsSummarySerializer(data).data)


@extend_schema(
    parameters=DATE_PARAMS,
    responses={200: MarketAnalyticsDetailSerializer},
)
class MarketAnalyticsDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAdminOrDeliverer]
    serializer_class = MarketAnalyticsDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        start, end = parse_optional_date_range(self.request.query_params)
        return annotate_market_analytics(_base_market_qs(), start, end)


@extend_schema(responses={200: MarketDebtOrderSerializer(many=True)})
class MarketDebtOrderListAPIView(ListAPIView):
    permission_classes = [IsAdminOrDeliverer]
    serializer_class = MarketDebtOrderSerializer
    pagination_class = MarketAnalyticsPagination

    def get_queryset(self):
        market_id = self.kwargs["id"]
        if not Market.objects.filter(id=market_id).exists():
            raise NotFound("Do'kon topilmadi")
        return (
            delivered_orders_with_remaining()
            .filter(market_id=market_id, remaining_debt__gt=0)
            .select_related("ordered_by", "delivered_by")
            .order_by("created_at", "id")
        )


@extend_schema(
    request=SingleMarketStatusUpdateSerializer,
    responses={200: OpenApiTypes.OBJECT},
)
class MarketStatusUpdateAPIView(APIView):
    permission_classes = [IsAdminOrDeliverer]

    def put(self, request, id, *args, **kwargs):
        serializer = SingleMarketStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not Market.objects.filter(id=id).exists():
            raise NotFound("Do'kon topilmadi")
        updated_ids, skipped = update_market_statuses(
            [id],
            serializer.validated_data["status"],
        )
        if not updated_ids:
            raise ValidationError(
                {"detail": skipped[0]["reason"] if skipped else "Yangilanmadi"}
            )
        return Response(
            {
                "id": updated_ids[0],
                "status": serializer.validated_data["status"],
            }
        )
