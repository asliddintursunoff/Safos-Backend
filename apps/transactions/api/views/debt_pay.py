from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import IsAdminOrDeliverer
from rest_framework.exceptions import ValidationError

from datetime import date, datetime

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Sum

from apps.orders.models import Order
from apps.markets.models import Market
from apps.transactions.models import PaymentAllocation, Payment
from apps.transactions.api.serializers import TakePaymentFromMarketCreateSerializer, PaymentSerializer
from apps.users.models import User
from apps.common.permissions import WORKER_ROLES, IsAdminRole


class WorkerStatisticsAPIView(APIView):
    permission_classes = [IsAdminRole]

    @staticmethod
    def parse_date(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None

    def get(self, request, *args, **kwargs):
        start_raw = request.query_params.get("start_date") or request.query_params.get("date")
        end_raw = request.query_params.get("end_date") or start_raw
        start_date = self.parse_date(start_raw) or date.today()
        end_date = self.parse_date(end_raw) or start_date

        if start_date > end_date:
            raise ValidationError("Boshlang'ich sana tugash sanadan keyin bo'lishi mumkin emas")

        workers = User.objects.filter(role_type__in=WORKER_ROLES).order_by("role_type", "first_name", "last_name")

        order_stats = (
            Order.objects.filter(
                delivered_by__isnull=False,
                status="DELIVERED",
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .values("delivered_by_id")
            .annotate(order_count=Count("id"), order_money=Sum("total_price_with_discount"))
        )
        order_map = {
            str(item["delivered_by_id"]): {
                "order_count": item["order_count"] or 0,
                "order_money": float(item["order_money"] or 0),
            }
            for item in order_stats
            if item.get("delivered_by_id")
        }

        payment_stats = (
            Payment.objects.filter(
                taken_by__isnull=False,
                payment_date__date__gte=start_date,
                payment_date__date__lte=end_date,
            )
            .values("taken_by_id")
            .annotate(payment_money=Sum("amount"))
        )
        payment_map = {
            str(item["taken_by_id"]): float(item["payment_money"] or 0)
            for item in payment_stats
            if item.get("taken_by_id")
        }

        result = []
        for worker in workers:
            worker_id = str(worker.id)
            stats = order_map.get(worker_id, {"order_count": 0, "order_money": 0})
            result.append({
                "id": str(worker.id),
                "name": f"{worker.first_name or ''} {worker.last_name or ''}".strip() or (worker.phone_number or "Noma'lum"),
                "role_type": worker.role_type,
                "phone_number": worker.phone_number,
                "order_count": stats["order_count"],
                "order_money": stats["order_money"],
                "payment_money": payment_map.get(worker_id, 0),
            })

        result.sort(key=lambda item: (-item["order_money"], -item["payment_money"], -item["order_count"], item["name"]))

        # Global totals for the requested range
        totals_orders = Order.objects.filter(
            delivered_by__isnull=False,
            status="DELIVERED",
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).aggregate(total_count=Count('id'), total_money=Sum('total_price_with_discount'))

        totals_payments = Payment.objects.filter(
            taken_by__isnull=False,
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
        ).aggregate(total_money=Sum('amount'))

        total_orders_count = int(totals_orders.get('total_count') or 0)
        total_orders_money = float(totals_orders.get('total_money') or 0)
        total_transactions_money = float(totals_payments.get('total_money') or 0)

        return Response({
            "start_date": start_date.strftime("%d/%m/%Y"),
            "end_date": end_date.strftime("%d/%m/%Y"),
            "total_orders": total_orders_count,
            "total_orders_money": total_orders_money,
            "total_transactions_money": total_transactions_money,
            "results": result,
        })


class TakePaymentFromMarketCreateAPIView(APIView):
    serializer_class = TakePaymentFromMarketCreateSerializer
    permission_classes = [IsAdminOrDeliverer]

    @staticmethod
    def parse_date(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None

    def get(self, request, *args, **kwargs):
        market_id = request.query_params.get("market_id")
        if market_id:
            qs = Payment.objects.filter(market_id=market_id).select_related("taken_by", "market").order_by("-payment_date", "-id")
            page_size = int(request.query_params.get("page_size", "40") or "40")
            page_size = max(1, min(page_size, 100))
            page = int(request.query_params.get("page", "1") or "1")
            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page)
            serializer = PaymentSerializer(page_obj.object_list, many=True)
            return Response({
                "count": paginator.count,
                "page": page_obj.number,
                "page_size": page_size,
                "next": page_obj.has_next(),
                "previous": page_obj.has_previous(),
                "results": serializer.data,
            })

        if getattr(request.user, "role_type", None) == "ADMIN":
            qs = Payment.objects.select_related("taken_by", "market").order_by("-payment_date", "-id")
        else:
            qs = Payment.objects.filter(taken_by=request.user).select_related("taken_by", "market").order_by("-payment_date", "-id")

        market_name = (request.query_params.get("market_name") or "").strip()
        if market_name:
            qs = qs.filter(market__name__icontains=market_name)

        day = self.parse_date(request.query_params.get("date"))
        if day:
            qs = qs.filter(payment_date__date=day)

        start_date = self.parse_date(request.query_params.get("start_date"))
        end_date = self.parse_date(request.query_params.get("end_date"))
        if start_date:
            qs = qs.filter(payment_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(payment_date__date__lte=end_date)

        page_size = int(request.query_params.get("page_size", "40") or "40")
        page_size = max(1, min(page_size, 100))
        page = int(request.query_params.get("page", "1") or "1")
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        serializer = PaymentSerializer(page_obj.object_list, many=True)
        today_total = qs.filter(payment_date__date=date.today()).aggregate(total=Sum("amount"))["total"] or 0

        return Response({
            "count": paginator.count,
            "page": page_obj.number,
            "page_size": page_size,
            "next": page_obj.has_next(),
            "previous": page_obj.has_previous(),
            "today_total": today_total,
            "results": serializer.data,
        })

    def post(self, request, *args, **kwargs):
        data = TakePaymentFromMarketCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        market_id = data.validated_data["market_id"]
        amount = data.validated_data["amount"]
        try:
            with transaction.atomic():
                payment = Payment.objects.create(market_id=market_id, amount=amount, taken_by=self.request.user)
                payment_allocation_bulk = []
                orders = list(
                    Order.objects.filter(market_id=market_id, is_debt_paid=False, status="DELIVERED")
                    .order_by("created_at")
                    .select_for_update()
                )
                payment_allocations = PaymentAllocation.objects.filter(order_id__in=[order.id for order in orders])
                payment_allocations_dict = {}
                for i in payment_allocations:
                    if i.order_id in payment_allocations_dict:
                        payment_allocations_dict[i.order_id] += i.allocated_amount
                    else:
                        payment_allocations_dict[i.order_id] = i.allocated_amount
                for order in orders:
                    price = order.total_price_with_discount - payment_allocations_dict.get(order.id, 0)
                    if amount <= 0:
                        break
                    if amount >= price:
                        order.is_debt_paid = True
                        amount = amount - price
                        payment_allocation_bulk.append(
                            PaymentAllocation(
                                payment=payment,
                                order=order,
                                allocated_amount=price,
                            )
                        )
                    else:
                        payment_allocation_bulk.append(
                            PaymentAllocation(
                                payment=payment,
                                order=order,
                                allocated_amount=amount,
                            )
                        )
                        amount = 0
                if amount > 0:
                    Market.objects.filter(id=market_id).update(credit_amount=F("credit_amount") + amount)
                Order.objects.bulk_update(orders, ["is_debt_paid"])
                PaymentAllocation.objects.bulk_create(payment_allocation_bulk)
                payment_allocation_bulk = []

            return Response({"transaction_id": payment.id})
        except IntegrityError:
            raise ValidationError("Tanlangan Do'kon mavjud emas")
        except Exception as e:
            raise ValidationError(str(e))
