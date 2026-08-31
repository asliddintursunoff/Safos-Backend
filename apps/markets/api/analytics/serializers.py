from rest_framework import serializers

from apps.common.choices import MARKET_STATUS_CHOICES
from apps.markets.services.analytics import (
    as_int_days,
    as_money,
    frequency_code_and_label,
)
from apps.users.api.serializers import UserBaseReadSerializer


class MarketVolumeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField(source="statuses.status", default=None)
    status_display = serializers.CharField(
        source="statuses.get_status_display", default=None
    )
    status_color_code = serializers.CharField(
        source="statuses.color_code", default=None
    )
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    ordered_amount = serializers.DecimalField(max_digits=20, decimal_places=3)
    ordered_amount_before_discount = serializers.DecimalField(
        max_digits=20, decimal_places=3
    )
    order_count = serializers.IntegerField()
    total_debt = serializers.DecimalField(max_digits=20, decimal_places=3)
    unpaid_order_count = serializers.IntegerField()
    credit_amount = serializers.DecimalField(max_digits=20, decimal_places=3)
    net_balance = serializers.SerializerMethodField()
    last_order_at = serializers.DateTimeField(allow_null=True)
    days_since_last_order = serializers.SerializerMethodField()
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_net_balance(self, obj):
        return as_money(obj.credit_amount) - as_money(obj.total_debt)

    def get_days_since_last_order(self, obj):
        return as_int_days(getattr(obj, "days_since_last_order", None))


class MarketActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField(source="statuses.status", default=None)
    status_display = serializers.CharField(
        source="statuses.get_status_display", default=None
    )
    status_color_code = serializers.CharField(
        source="statuses.color_code", default=None
    )
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    last_order_at = serializers.DateTimeField(allow_null=True)
    first_order_at = serializers.DateTimeField(allow_null=True)
    days_since_last_order = serializers.SerializerMethodField()
    avg_days_between_orders = serializers.FloatField(allow_null=True)
    frequency_code = serializers.SerializerMethodField()
    frequency_label = serializers.SerializerMethodField()
    taken_order_count = serializers.IntegerField()
    delivered_order_count = serializers.IntegerField()
    never_ordered = serializers.SerializerMethodField()
    total_debt = serializers.DecimalField(max_digits=20, decimal_places=3)
    unpaid_order_count = serializers.IntegerField()
    credit_amount = serializers.DecimalField(max_digits=20, decimal_places=3)
    open_order_count = serializers.IntegerField()

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_days_since_last_order(self, obj):
        return as_int_days(getattr(obj, "days_since_last_order", None))

    def get_never_ordered(self, obj):
        return obj.last_order_at is None

    def _frequency(self, obj):
        return frequency_code_and_label(
            obj.avg_days_between_orders,
            obj.taken_order_count,
        )

    def get_frequency_code(self, obj):
        return self._frequency(obj)[0]

    def get_frequency_label(self, obj):
        return self._frequency(obj)[1]


class MarketAnalyticsDetailSerializer(MarketVolumeSerializer):
    description = serializers.CharField()
    owner = UserBaseReadSerializer(allow_null=True)
    delivered_order_count = serializers.IntegerField()
    taken_order_count = serializers.IntegerField()
    open_order_count = serializers.IntegerField()
    cancelled_order_count = serializers.IntegerField()
    first_order_at = serializers.DateTimeField(allow_null=True)
    last_delivered_at = serializers.DateTimeField(allow_null=True)
    oldest_unpaid_order_at = serializers.DateTimeField(allow_null=True)
    avg_days_between_orders = serializers.FloatField(allow_null=True)
    frequency_code = serializers.SerializerMethodField()
    frequency_label = serializers.SerializerMethodField()
    never_ordered = serializers.SerializerMethodField()

    def get_never_ordered(self, obj):
        return obj.last_order_at is None

    def _frequency(self, obj):
        return frequency_code_and_label(
            obj.avg_days_between_orders,
            obj.taken_order_count,
        )

    def get_frequency_code(self, obj):
        return self._frequency(obj)[0]

    def get_frequency_label(self, obj):
        return self._frequency(obj)[1]


class MarketDebtOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    total_price = serializers.DecimalField(max_digits=20, decimal_places=3)
    total_price_with_discount = serializers.DecimalField(
        max_digits=20, decimal_places=3
    )
    allocated_amount = serializers.DecimalField(max_digits=20, decimal_places=3)
    remaining_debt = serializers.DecimalField(max_digits=20, decimal_places=3)
    is_debt_paid = serializers.BooleanField()
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M")
    delivered_at = serializers.DateTimeField(
        format="%d-%m-%Y %H:%M", allow_null=True
    )
    ordered_by = UserBaseReadSerializer(allow_null=True)
    delivered_by = UserBaseReadSerializer(allow_null=True)


class BulkMarketStatusUpdateSerializer(serializers.Serializer):
    market_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        max_length=500,
    )
    status = serializers.ChoiceField(choices=list(MARKET_STATUS_CHOICES.keys()))

    def validate_market_ids(self, value):
        unique = list(dict.fromkeys(value))
        if len(unique) != len(value):
            raise serializers.ValidationError(
                "market_ids ichida takroriy id bo'lmasligi kerak"
            )
        return unique


class SingleMarketStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=list(MARKET_STATUS_CHOICES.keys()))


class AnalyticsSummarySerializer(serializers.Serializer):
    market_count = serializers.IntegerField()
    markets_with_debt = serializers.IntegerField()
    total_debt = serializers.DecimalField(max_digits=20, decimal_places=3)
    total_credit = serializers.DecimalField(max_digits=20, decimal_places=3)
    never_ordered = serializers.IntegerField()
    inactive_over_7_days = serializers.IntegerField()
    inactive_over_30_days = serializers.IntegerField()
    open_orders_count = serializers.IntegerField()
    delivered_today_count = serializers.IntegerField()
    delivered_today_amount = serializers.DecimalField(
        max_digits=20, decimal_places=3
    )
    status_counts = serializers.DictField(
        child=serializers.IntegerField()
    )
