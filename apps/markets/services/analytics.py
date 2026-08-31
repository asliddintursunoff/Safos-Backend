from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Case,
    Count,
    DecimalField,
    DurationField,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Extract, Greatest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.choices import MARKET_STATUS_CHOICES
from apps.markets.models import Market, MarketStatus
from apps.orders.models import Order
from apps.orders.utils import parse_date
from apps.transactions.models import PaymentAllocation

MONEY = DecimalField(max_digits=20, decimal_places=3)
ZERO_MONEY = Value(Decimal("0.000"), output_field=MONEY)
TAKEN_ORDER_STATUSES = ("PENDING", "APPROVED", "DELIVERED")
OPEN_ORDER_STATUSES = ("PENDING", "APPROVED")
ACTIVE_MARKET_STATUSES = ("PENDING", "WAITING")

VOLUME_ORDERING = {
    "ordered_amount": F("ordered_amount").asc(nulls_last=True),
    "-ordered_amount": F("ordered_amount").desc(nulls_last=True),
    "order_count": F("order_count").asc(nulls_last=True),
    "-order_count": F("order_count").desc(nulls_last=True),
    "total_debt": F("total_debt").asc(nulls_last=True),
    "-total_debt": F("total_debt").desc(nulls_last=True),
    "name": F("name").asc(),
    "-name": F("name").desc(),
}

ACTIVITY_ORDERING = {
    "days_since_last_order": F("days_since_last_order").asc(nulls_last=True),
    "-days_since_last_order": F("days_since_last_order").desc(nulls_first=True),
    "avg_days_between_orders": F("avg_days_between_orders").asc(nulls_last=True),
    "-avg_days_between_orders": F("avg_days_between_orders").desc(nulls_last=True),
    "delivered_order_count": F("delivered_order_count").asc(nulls_last=True),
    "-delivered_order_count": F("delivered_order_count").desc(nulls_last=True),
    "taken_order_count": F("taken_order_count").asc(nulls_last=True),
    "-taken_order_count": F("taken_order_count").desc(nulls_last=True),
    "total_debt": F("total_debt").asc(nulls_last=True),
    "-total_debt": F("total_debt").desc(nulls_last=True),
    "name": F("name").asc(),
    "-name": F("name").desc(),
}


def money_zero():
    return Decimal("0.000")


def allocated_amount_subquery():
    """Per-order sum of PaymentAllocation.allocated_amount."""
    return Subquery(
        PaymentAllocation.objects.filter(order_id=OuterRef("pk"))
        .values("order_id")
        .annotate(total=Sum("allocated_amount"))
        .values("total")[:1],
        output_field=MONEY,
    )


def remaining_debt_expression():
    """
    max(total_price_with_discount - allocated, 0).

    Remaining unpaid amount is the source of truth, not is_debt_paid.
    """
    return Greatest(
        F("total_price_with_discount")
        - Coalesce(allocated_amount_subquery(), ZERO_MONEY),
        ZERO_MONEY,
        output_field=MONEY,
    )


def delivered_orders_with_remaining():
    return (
        Order.objects.filter(status="DELIVERED")
        .annotate(
            allocated_amount=Coalesce(allocated_amount_subquery(), ZERO_MONEY),
            remaining_debt=remaining_debt_expression(),
        )
    )


def market_total_debt_subquery():
    """Current unpaid delivered remainder per market. Not date-ranged."""
    return Subquery(
        delivered_orders_with_remaining()
        .filter(market_id=OuterRef("pk"))
        .values("market_id")
        .annotate(total=Sum("remaining_debt"))
        .values("total")[:1],
        output_field=MONEY,
    )


def market_unpaid_order_count_subquery():
    return Subquery(
        delivered_orders_with_remaining()
        .filter(market_id=OuterRef("pk"), remaining_debt__gt=0)
        .values("market_id")
        .annotate(total=Count("id"))
        .values("total")[:1],
        output_field=IntegerField(),
    )


def market_oldest_unpaid_at_subquery():
    return Subquery(
        delivered_orders_with_remaining()
        .filter(market_id=OuterRef("pk"), remaining_debt__gt=0)
        .values("market_id")
        .annotate(oldest=Min("created_at"))
        .values("oldest")[:1],
    )


def parse_optional_date_range(query_params):
    """
    Optional:
      date=dd-mm-yyyy
      start_date=dd-mm-yyyy & end_date=dd-mm-yyyy
    Applies only to order volume, never to debt.
    """
    date_str = query_params.get("date")
    start_str = query_params.get("start_date")
    end_str = query_params.get("end_date")

    if date_str:
        if start_str or end_str:
            raise ValidationError(
                "date bilan start_date/end_date birga ishlatilmaydi"
            )
        day = parse_date(date_str)
        return day, day

    if start_str or end_str:
        if not (start_str and end_str):
            raise ValidationError(
                "start_date va end_date ikkalasi ham berilishi kerak"
            )
        start = parse_date(start_str)
        end = parse_date(end_str)
        if start > end:
            raise ValidationError(
                "start_date end_date dan katta bo'lmasligi kerak"
            )
        return start, end

    return None, None


def parse_bool_param(query_params, name):
    raw = query_params.get(name)
    if raw is None or raw == "":
        return None
    lowered = str(raw).strip().lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    raise ValidationError({name: "true yoki false bo'lishi kerak"})


def parse_inactive_days(query_params):
    raw = query_params.get("inactive_days")
    if raw is None or raw == "":
        return None
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({"inactive_days": "butun son bo'lishi kerak"})
    if days < 1:
        raise ValidationError(
            {"inactive_days": "1 dan kichik bo'lmasligi kerak"}
        )
    return days


def parse_ordering(query_params, allowed, default):
    raw = query_params.get("ordering") or default
    if raw not in allowed:
        raise ValidationError(
            {
                "ordering": (
                    "Ruxsat etilgan qiymatlar: "
                    + ", ".join(sorted(allowed.keys()))
                )
            }
        )
    return allowed[raw]


def volume_order_q(start_date: date | None, end_date: date | None) -> Q:
    q = Q(orders__status="DELIVERED")
    if start_date:
        q &= Q(orders__created_at__date__gte=start_date)
    if end_date:
        q &= Q(orders__created_at__date__lte=end_date)
    return q


def annotate_market_analytics(queryset, start_date=None, end_date=None):
    """
    ordered_* fields respect the optional date range.
    total_debt / unpaid_order_count / credit_amount do not.
    """
    volume_q = volume_order_q(start_date, end_date)
    delivered_q = Q(orders__status="DELIVERED")
    taken_q = Q(orders__status__in=TAKEN_ORDER_STATUSES)
    open_q = Q(orders__status__in=OPEN_ORDER_STATUSES)

    return (
        queryset.annotate(
            ordered_amount=Coalesce(
                Sum(
                    "orders__total_price_with_discount",
                    filter=volume_q,
                    output_field=MONEY,
                ),
                ZERO_MONEY,
            ),
            ordered_amount_before_discount=Coalesce(
                Sum(
                    "orders__total_price",
                    filter=volume_q,
                    output_field=MONEY,
                ),
                ZERO_MONEY,
            ),
            order_count=Count("orders", filter=volume_q, distinct=True),
            delivered_order_count=Count(
                "orders", filter=delivered_q, distinct=True
            ),
            taken_order_count=Count("orders", filter=taken_q, distinct=True),
            open_order_count=Count("orders", filter=open_q, distinct=True),
            cancelled_order_count=Count(
                "orders",
                filter=Q(orders__status__in=["CANCELLED", "REJECTED"]),
                distinct=True,
            ),
            first_order_at=Min("orders__created_at", filter=taken_q),
            last_order_at=Max("orders__created_at", filter=taken_q),
            last_delivered_at=Max("orders__delivered_at", filter=delivered_q),
            total_debt=Coalesce(market_total_debt_subquery(), ZERO_MONEY),
            unpaid_order_count=Coalesce(
                market_unpaid_order_count_subquery(),
                Value(0),
            ),
            oldest_unpaid_order_at=market_oldest_unpaid_at_subquery(),
        )
        .annotate(
            activity_anchor=Coalesce(F("last_order_at"), F("created_at")),
        )
        .annotate(
            days_since_last_order=ExpressionWrapper(
                Extract(
                    ExpressionWrapper(
                        timezone.now() - F("activity_anchor"),
                        output_field=DurationField(),
                    ),
                    "epoch",
                )
                / Value(86400.0),
                output_field=FloatField(),
            ),
            avg_days_between_orders=Case(
                When(
                    taken_order_count__lte=1,
                    then=Value(None, output_field=FloatField()),
                ),
                default=ExpressionWrapper(
                    Extract(
                        ExpressionWrapper(
                            F("last_order_at") - F("first_order_at"),
                            output_field=DurationField(),
                        ),
                        "epoch",
                    )
                    / (
                        Value(86400.0)
                        * (F("taken_order_count") - Value(1))
                    ),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            ),
        )
    )


def apply_has_debt_filter(queryset, has_debt):
    if has_debt is True:
        return queryset.filter(total_debt__gt=0)
    if has_debt is False:
        return queryset.filter(total_debt=0)
    return queryset


def apply_inactive_days_filter(queryset, inactive_days):
    if inactive_days is None:
        return queryset
    cutoff = timezone.now() - timedelta(days=inactive_days)
    return queryset.filter(activity_anchor__lte=cutoff)


def frequency_code_and_label(avg_days, taken_order_count):
    if not taken_order_count:
        return "NEVER", "Buyurtma yo'q"
    if taken_order_count == 1 or avg_days is None:
        return "SINGLE_ORDER", "1 ta buyurtma"
    avg = float(avg_days)
    if avg <= 1.5:
        return "EVERY_DAY", "Har kuni"
    if avg <= 3.5:
        return "EVERY_3_DAYS", "Har 3 kunda"
    if avg <= 5.5:
        return "EVERY_5_DAYS", "Har 5 kunda"
    if avg <= 8.5:
        return "EVERY_WEEK", "Har hafta"
    if avg <= 16:
        return "EVERY_2_WEEKS", "Har 2 haftada"
    if avg <= 35:
        return "EVERY_MONTH", "Har oyda"
    return "RARELY", "Kamdan-kam"


def as_money(value) -> Decimal:
    if value is None:
        return money_zero()
    return Decimal(value).quantize(Decimal("0.001"))


def as_int_days(value):
    if value is None:
        return None
    return int(value)


def status_color_for(status: str) -> str:
    if status in MARKET_STATUS_CHOICES:
        return status
    return "NOT_NEEDED"


@transaction.atomic
def update_market_statuses(market_ids, new_status):
    """
    Lock markets in id order so this cannot deadlock with order-create,
    which also select_for_update()s Market.

    Do not select_related statuses here: that LEFT JOIN cannot be locked
    with FOR UPDATE on Postgres.

    Markets with an open order or WAITING/PENDING status are skipped.
    """
    ordered_ids = sorted(market_ids)
    markets = list(
        Market.objects.select_for_update()
        .filter(id__in=ordered_ids)
        .order_by("id")
    )
    found_ids = {market.id for market in markets}
    missing = [market_id for market_id in ordered_ids if market_id not in found_ids]
    if missing:
        raise ValidationError({"market_ids": "Ba'zi do'konlar topilmadi"})

    market_pk_list = [market.id for market in markets]
    status_by_market = {
        row.market_id: row
        for row in MarketStatus.objects.select_for_update()
        .filter(market_id__in=market_pk_list)
        .order_by("market_id")
    }

    open_ids = set(
        Order.objects.filter(
            market_id__in=ordered_ids,
            status__in=OPEN_ORDER_STATUSES,
        ).values_list("market_id", flat=True)
    )

    to_update = []
    skipped = []
    updated_ids = []
    color = status_color_for(new_status)

    for market in markets:
        status_obj = status_by_market.get(market.id)
        if status_obj is None:
            skipped.append(
                {
                    "id": str(market.id),
                    "name": market.name,
                    "reason": "Do'kon holati topilmadi",
                }
            )
            continue
        if market.id in open_ids or status_obj.status in ACTIVE_MARKET_STATUSES:
            skipped.append(
                {
                    "id": str(market.id),
                    "name": market.name,
                    "reason": "Do'konda faol buyurtma bor, holat o'zgartirilmadi",
                }
            )
            continue
        status_obj.status = new_status
        status_obj.color_code = color
        to_update.append(status_obj)
        updated_ids.append(market.id)

    if to_update:
        MarketStatus.objects.bulk_update(to_update, ["status", "color_code"])

    return updated_ids, skipped


def volume_list_summary(queryset):
    total_ordered_amount = money_zero()
    total_debt = money_zero()
    markets_with_debt = 0
    for row in queryset.order_by().values("ordered_amount", "total_debt"):
        ordered = as_money(row["ordered_amount"])
        debt = as_money(row["total_debt"])
        total_ordered_amount += ordered
        total_debt += debt
        if debt > 0:
            markets_with_debt += 1
    return {
        "total_ordered_amount": total_ordered_amount,
        "total_debt": total_debt,
        "markets_with_debt": markets_with_debt,
    }


def dashboard_summary():
    qs = annotate_market_analytics(Market.objects.all())
    today = timezone.localdate()

    market_count = 0
    markets_with_debt = 0
    total_debt = money_zero()
    total_credit = money_zero()
    never_ordered = 0
    inactive_over_7_days = 0
    inactive_over_30_days = 0

    for row in qs.order_by().values(
        "total_debt",
        "credit_amount",
        "last_order_at",
        "days_since_last_order",
    ):
        market_count += 1
        debt = as_money(row["total_debt"])
        total_debt += debt
        total_credit += as_money(row["credit_amount"])
        if debt > 0:
            markets_with_debt += 1
        if row["last_order_at"] is None:
            never_ordered += 1
        days = row["days_since_last_order"]
        if days is not None and days >= 7:
            inactive_over_7_days += 1
        if days is not None and days >= 30:
            inactive_over_30_days += 1

    delivered_today = Order.objects.filter(
        status="DELIVERED",
        delivered_at__date=today,
    ).aggregate(
        delivered_today_count=Count("id"),
        delivered_today_amount=Coalesce(
            Sum("total_price_with_discount"),
            ZERO_MONEY,
        ),
    )
    status_counts = {key: 0 for key in MARKET_STATUS_CHOICES}
    for row in MarketStatus.objects.values("status").annotate(count=Count("id")):
        status_counts[row["status"]] = row["count"]

    return {
        "market_count": market_count,
        "markets_with_debt": markets_with_debt,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "never_ordered": never_ordered,
        "inactive_over_7_days": inactive_over_7_days,
        "inactive_over_30_days": inactive_over_30_days,
        "delivered_today_count": delivered_today["delivered_today_count"] or 0,
        "delivered_today_amount": as_money(
            delivered_today["delivered_today_amount"]
        ),
        "open_orders_count": Order.objects.filter(
            status__in=OPEN_ORDER_STATUSES
        ).count(),
        "status_counts": status_counts,
    }
