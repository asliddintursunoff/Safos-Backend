from django_filters import rest_framework as filters

from apps.orders.models import Order
from apps.common.choices import ORDER_STATUS_CHOICES


class OrderFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(
        field_name="status",
        choices=tuple(ORDER_STATUS_CHOICES.items()),
    )
    is_debt_paid = filters.BooleanFilter(field_name="is_debt_paid")
    market_id = filters.UUIDFilter(field_name="market_id")
    date = filters.DateFilter(field_name="created_at", lookup_expr="date")
    specific_date = filters.DateFilter(field_name="created_at", lookup_expr="date")
    created_date_after = filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte"
    )
    created_date_before = filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte"
    )
    class Meta:
        model = Order
        fields = ['status', 'market_id', 'date', 'specific_date']
        
