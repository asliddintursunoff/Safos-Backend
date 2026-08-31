from django.db.models import Sum,F, Value, Count,DecimalField,FloatField, ExpressionWrapper

from rest_framework.views  import APIView
from rest_framework.generics import ListAPIView,GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from decimal import Decimal

from django.db.models import (
    Sum, F, Case, When, Value, DecimalField
)
from django.db.models.functions import Coalesce

from apps.orders.api.permissions import IsADMIN, IsAdminOrDeliverer
from apps.orders.models import OrderItem,Order,OrderItemConribution
from apps.orders.utils import get_date_filters,parse_date
from apps.orders.api.serializers.todays_orders import (DeliveringTotalOrdersSerializer,
                                                       DeliveringMarketOrderSerializer,
                                                       MyOrdersTotalPriceSerializer,
                                                       TotalPriceByAllUsersOrderSerializer)


class TodaysDeliveringOrdersCountAPIView(APIView):
    permission_classes = [IsAdminOrDeliverer]
    def get(self, request, *args, **kwargs):
        product_queryset = (
            OrderItem.objects
            .filter(order__status="APPROVED")
            .values(
                product_name=F("product__name"),
                unit=F("product__unit"),
                value=F("product__value"),
            )
            .annotate(
                total_quantity=Sum("quantity"),

                total_price=Sum(
                    ExpressionWrapper(
                        F("quantity") * F("product__price"),
                        output_field=DecimalField(
                            max_digits=20,
                            decimal_places=3,
                        ),
                    )
                ),
            )
            .order_by("product_name")
        )
        total_sum_query = (
            OrderItem.objects
            .filter(order__status="APPROVED")
            .aggregate(
                total_count_of_orders=Count(
                    "order_id",
                    distinct=True,
                ),

                total_price=Sum(
                    ExpressionWrapper(
                        F("quantity") * F("product__price"),
                        output_field=DecimalField(
                            max_digits=20,
                            decimal_places=3,
                        ),
                    )
                ),

                total_price_with_discount=Sum(
                    ExpressionWrapper(
                        F("quantity")
                        * F("product__price")
                        * (
                            Value(1)
                            - F("order__market__discount_percentage")
                            / Value(100)
                        ),
                        output_field=DecimalField(
                            max_digits=20,
                            decimal_places=3,
                        ),
                    )
                ),
            )
        )
        data = {
            "total_count_of_orders": total_sum_query["total_count_of_orders"] or 0,
            "total_price": total_sum_query["total_price"] or 0,
            "total_price_with_discount": (
                total_sum_query["total_price_with_discount"] or 0
            ),
            "counts_of_each_product": product_queryset,
        }
        serializer = DeliveringTotalOrdersSerializer(data)

        return Response(serializer.data)
    
class TodaysDeliveringMarketsListAPIView(ListAPIView):
    queryset = Order.objects.filter(status='APPROVED').select_related(
        'market', 'market__statuses'
    )
    serializer_class = DeliveringMarketOrderSerializer
    permission_classes = [IsAdminOrDeliverer]
    
    
@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Single day filter. Format: **dd-mm-yyyy** (example: `25-08-2026`). "
                        "Use this **OR** the range parameters below.",
            required=False,
        ),
        OpenApiParameter(
            name="start_date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Start of date range. Format: **dd-mm-yyyy**",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="End of date range. Format: **dd-mm-yyyy**",
            required=False,
        ),
    ],
    responses={200: MyOrdersTotalPriceSerializer},
)
class MyOrdersTotalPriceAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyOrdersTotalPriceSerializer

    def get_queryset(self):
        date_filters = get_date_filters(self.request)

        price_expr = F("quantity") * F("product__price")

        return (
            OrderItemConribution.objects
            .filter(ordered_by=self.request.user, **date_filters)
            .aggregate(
                total=Coalesce(
                    Sum(price_expr),
                    Value(Decimal("0.000")),
                    output_field=DecimalField(max_digits=20, decimal_places=3),
                ),
                
                delivered=Coalesce(
                    Sum(
                        Case(
                            When(order__status="DELIVERED", then=price_expr),
                            default=Value(0),
                            output_field=DecimalField(max_digits=20, decimal_places=3),
                        )
                    ),
                    Value(Decimal("0.000")),
                    output_field=DecimalField(max_digits=20, decimal_places=3),
                ),
            )
        )

    def get(self, request):
        result = self.get_queryset()
        serializer = self.get_serializer(result)
        return Response(serializer.data)



@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Single day filter. Format: **dd-mm-yyyy** (example: `25-08-2026`). "
                        "Use this **OR** the range parameters below.",
            required=False,
        ),
        OpenApiParameter(
            name="start_date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Start of date range. Format: **dd-mm-yyyy**",
            required=False,
        ),
        OpenApiParameter(
            name="end_date",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="End of date range. Format: **dd-mm-yyyy**",
            required=False,
        ),
    ],
    responses={200: TotalPriceByAllUsersOrderSerializer(many=True)},
)
class TotalPriceByAllUsersOrderAPIView(ListAPIView):
    permission_classes = [IsADMIN]
    serializer_class = TotalPriceByAllUsersOrderSerializer

    def get_queryset(self):
        date_filters = get_date_filters(self.request)

        price_expr = F("quantity") * F("product__price")

        return (
            OrderItemConribution.objects
            .filter(**date_filters)
            .values(
                user_id=F("ordered_by__id"),
                user_first_name=F("ordered_by__first_name"),
                user_last_name=F("ordered_by__last_name"),
            )
            .annotate(
                total=Coalesce(
                    Sum(price_expr),
                    Value(Decimal("0.000")),
                    output_field=DecimalField(max_digits=20, decimal_places=3),
                ),
                
                delivered=Coalesce(
                    Sum(
                        Case(
                            When(order__status="DELIVERED", then=price_expr),
                            default=Value(0),
                            output_field=DecimalField(max_digits=20, decimal_places=3),
                        )
                    ),
                    Value(Decimal("0.000")),
                    output_field=DecimalField(max_digits=20, decimal_places=3),
                ),
            )
            .order_by("-total")         
        )