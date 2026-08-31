from django.db import transaction
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

from apps.common.permissions import CanCreateMarket
from apps.markets.api.filters import MarketFilter
from apps.markets.models import Market, MarketStatus
from .serializers import MarketListSerializer, MarketCreateSerializer, MarketReadSerializer


class MarketListCreateAPIView(ListCreateAPIView):
    queryset = Market.objects.select_related("statuses")
    filterset_class = MarketFilter
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    permission_classes = [CanCreateMarket]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = Market.objects.select_related(
            "statuses",
            "owner",
            "statuses__last_order",
            "statuses__last_order__ordered_by",
        )
        user = self.request.user
        if getattr(user, "role_type", None) == "CUSTOMER":
            queryset = queryset.filter(owner=user)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        latitude = self.request.query_params.get("latitude")
        longitude = self.request.query_params.get("longitude")
        if latitude and longitude:
            point = Point(float(longitude), float(latitude), srid=4326)
            queryset = queryset.filter(location__isnull=False).annotate(
                distance=Distance("location", point)
            ).order_by("distance")
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MarketCreateSerializer
        return MarketListSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        market = serializer.save()
        MarketStatus.objects.get_or_create(market=market)


class MarketRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Market.objects.select_related(
        "statuses",
        "owner",
        "created_by",
        "statuses__last_order",
        "statuses__last_order__ordered_by",
        "statuses__last_order__delivered_by",
    )
    serializer_class = MarketReadSerializer
    lookup_field = "id"
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [CanCreateMarket]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "role_type", None) == "CUSTOMER":
            return queryset.filter(owner=user)
        return queryset

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return MarketCreateSerializer
        return MarketReadSerializer
