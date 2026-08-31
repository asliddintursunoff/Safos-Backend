from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F
from rest_framework.exceptions import ValidationError

from apps.markets.models import Market
from apps.orders.models import Order, OrderItem, OrderItemConribution
from apps.orders.api.serializers.crud import (
    CreateOrderSerializer,
    OrderDetailSerializer,
    ListReadOrderSerializer,
    UpdateOrderSerializer,
    OrderStatusUpdateSerializer
)
from apps.orders.services.transaction_from_market_credit import (
    pay_from_market_credit,
    refund_market_credit_from_order,
)
from ..filters import OrderFilter
from ..pagination import OrderPageNumber
from ..permissions import CanCreateOrder, CanUserUpdateDeleteOrder, IsAdminOrDeliverer


class ListCreateOrderAPIView(ListCreateAPIView):
    queryset = Order.objects.select_related('market').order_by('-created_at')
    serializer_class = CreateOrderSerializer
    permission_classes = [IsAuthenticated, CanCreateOrder]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = OrderFilter
    search_fields = ['market__name']
    pagination_class = OrderPageNumber

    def get_queryset(self):
        qs = Order.objects.select_related(
            "market", "ordered_by", "delivered_by"
        ).order_by("-created_at")
        user = self.request.user
        role = getattr(user, "role_type", None)
        if role in ("ADMIN", "DELIVERER"):
            return qs
        if role == "CUSTOMER":
            return qs.filter(market__owner=user)
        return qs.filter(ordered_by=user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return ListReadOrderSerializer

    def perform_create(self, serializer):
        market_id = serializer.validated_data['market_id']
        items = serializer.validated_data['items']
        user = self.request.user

        with transaction.atomic():
            try:
                market = Market.objects.select_for_update().get(id=market_id)
            except Market.DoesNotExist:
                raise ValidationError({"market_id": "Bunday id dagi do'kon topilmadi"})
            if user.role_type == "CUSTOMER" and market.owner_id != user.id:
                raise ValidationError({"market_id": "Bu do'kon sizniki emas"})

            if hasattr(market, 'statuses') and market.statuses.status in ['WAITING', 'PENDING']:
                raise ValidationError({"detail": "Bu Do'kondan allaqachon buyurtma olingan"})

            order = Order.objects.create(market_id=market_id, ordered_by=user)

            order_items_bulk = []
            contrib_items_bulk = []

            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']

                order_items_bulk.append(
                    OrderItem(order=order, product_id=product_id, quantity=quantity)
                )
                contrib_items_bulk.append(
                    OrderItemConribution(
                        order=order,
                        product_id=product_id,
                        ordered_by=user,
                        quantity=quantity,
                        peak_quantity=quantity  # Set initial peak equal to initial quantity
                    )
                )

            OrderItem.objects.bulk_create(order_items_bulk)
            OrderItemConribution.objects.bulk_create(contrib_items_bulk)

            total_sum = OrderItem.objects.filter(order=order).aggregate(
                sum=Sum(F('quantity') * F('product__price'))
            )['sum'] or Decimal("0")

            if total_sum < 0:
                raise ValidationError("Umumiy pul 0 so'mdan kichik bo'la olmaydi.")

            discount_amount = (total_sum / Decimal("100")) * market.discount_percentage
            order.total_price = total_sum
            order.total_price_with_discount = total_sum - discount_amount
            order.save()
            order.market = market
            pay_from_market_credit(order)

            if hasattr(market, 'statuses'):
                market.statuses.color_code = 'PENDING'
                market.statuses.status = 'PENDING'
                market.statuses.last_order = order
                market.statuses.save()

        serializer.instance = order


class OrderDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.select_related(
        'market', 'market__owner', 'ordered_by', 'delivered_by'
    ).prefetch_related('items')
    lookup_field = 'id'
    permission_classes = [CanUserUpdateDeleteOrder]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role_type", None)
        if role in ("ADMIN", "DELIVERER", "AGENT"):
            return qs
        if role == "CUSTOMER":
            return qs.filter(market__owner=user)
        return qs.filter(ordered_by=user)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == 'GET':
            return OrderDetailSerializer
        return UpdateOrderSerializer

    def perform_update(self, serializer):
        items = serializer.validated_data["items"]
        order = self.get_object()
        current_user = self.request.user

        # Dict of target quantities from request payload: {product_id: quantity}
        target_quantities = {item['product_id']: item['quantity'] for item in items}

        with transaction.atomic():
            # 1. Zero out products removed entirely from incoming payload
            all_existing_contrib_pids = set(
                OrderItemConribution.objects.filter(order=order).values_list('product_id', flat=True)
            )
            removed_pids = all_existing_contrib_pids - set(target_quantities.keys())

            if removed_pids:
                OrderItemConribution.objects.filter(
                    order=order,
                    product_id__in=removed_pids
                ).update(quantity=0)

            # 2. Process each product in incoming payload
            for prod_id, target_qty in target_quantities.items():
                contribs = list(
                    OrderItemConribution.objects.filter(
                        order=order,
                        product_id=prod_id
                    ).order_by('created_at')
                )

                current_total = sum(c.quantity for c in contribs)

                if target_qty < current_total:
                    # REDUCTION: Reduce from existing contributors in reverse order (LIFO)
                    to_reduce = current_total - target_qty
                    for contrib in reversed(contribs):
                        if to_reduce <= 0:
                            break
                        reduced = min(contrib.quantity, to_reduce)
                        contrib.quantity -= reduced
                        to_reduce -= reduced
                        contrib.save()  # peak_quantity remains unchanged

                elif target_qty > current_total:
                    # INCREASE: Restore lost baseline first (FIFO), then assign excess
                    extra = target_qty - current_total

                    # Step A: Restore original contributors up to their peak_quantity
                    for contrib in contribs:
                        if extra <= 0:
                            break
                        deficit = contrib.peak_quantity - contrib.quantity
                        if deficit > 0:
                            restored = min(deficit, extra)
                            contrib.quantity += restored
                            extra -= restored
                            contrib.save()

                    # Step B: Assign remaining excess to current editing user
                    if extra > 0:
                        user_contrib, _ = OrderItemConribution.objects.get_or_create(
                            order=order,
                            product_id=prod_id,
                            ordered_by=current_user,
                            defaults={'quantity': 0, 'peak_quantity': 0}
                        )
                        user_contrib.quantity += extra
                        user_contrib.peak_quantity = max(
                            user_contrib.peak_quantity,
                            user_contrib.quantity
                        )
                        user_contrib.save()

            # 3. Refresh OrderItem list
            OrderItem.objects.filter(order=order).delete()
            new_order_items = [
                OrderItem(order=order, product_id=pid, quantity=qty)
                for pid, qty in target_quantities.items()
                if qty > 0
            ]
            OrderItem.objects.bulk_create(new_order_items)

            # 4. Recalculate totals
            result = OrderItem.objects.filter(order=order).aggregate(
                sum=Sum(F("quantity") * F("product__price"))
            )
            total_price = result["sum"] or Decimal("0")

            if total_price < 0:
                raise ValidationError({"detail": "Umumiy pul 0 so'mdan kichik bo'la olmaydi."})

            discount_price = (total_price / Decimal("100")) * order.market.discount_percentage

            order.total_price = total_price
            order.total_price_with_discount = total_price - discount_price
            order.save()
            pay_from_market_credit(order)

            if hasattr(order.market, 'statuses'):
                order.market.statuses.color_code = "PENDING"
                order.market.statuses.status = "PENDING"
                order.market.statuses.last_order = order
                order.market.statuses.save()

        serializer.instance = order

    @transaction.atomic
    def perform_destroy(self, instance):
        refund_market_credit_from_order(instance)
        market = instance.market
        if hasattr(market, 'statuses'):
            market.statuses.status = 'POSSIBLE'
            market.statuses.color_code = 'POSSIBLE'

            if market.statuses.last_order_id == instance.id:
                market.statuses.last_order = None
                
            market.statuses.save()
        return super().perform_destroy(instance)

class OrderStatusUpdateAPIView(UpdateAPIView):
    queryset = Order.objects.select_related("market", "market__statuses")
    serializer_class = OrderStatusUpdateSerializer
    lookup_field = 'id'
    permission_classes = [IsAdminOrDeliverer]
    
    
