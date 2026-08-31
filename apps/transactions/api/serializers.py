from rest_framework import serializers

from apps.transactions.models import Payment, PaymentAllocation
from apps.users.api.serializers import UserBaseReadSerializer


class TakePaymentFromMarketCreateSerializer(serializers.Serializer):
    market_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=3)

    def validate_amount(self, value):
        if value > 0:
            return value
        raise serializers.ValidationError("qiymat 0 dan katta bo'lishi kerak")


class PaymentSerializer(serializers.ModelSerializer):
    taken_by = UserBaseReadSerializer(allow_null=True)
    allocated_total = serializers.SerializerMethodField()
    market_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "amount", "payment_date", "taken_by", "market_name", "allocated_total"]

    def get_allocated_total(self, obj):
        try:
            from django.db.models import Sum

            s = PaymentAllocation.objects.filter(payment=obj).aggregate(t=Sum("allocated_amount"))["t"]
            return s or 0
        except Exception:
            return 0

    def get_market_name(self, obj):
        return obj.market.name if obj.market else ""

