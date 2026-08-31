from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.markets.models import Market, MarketStatus
from apps.markets.services.analytics import (
    OPEN_ORDER_STATUSES,
    status_color_for,
)
from apps.orders.models import Order

DEFAULT_REFRESH_DAYS = 5
MIN_DELIVERED_FOR_CADENCE = 3
TARGET_STATUS = "POSSIBLE"
SOURCE_STATUS = "AVAILABLE"


def _as_local_date(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    return value.date()


def cadence_interval_days(created_at_list, default_days=None):
    """
    Default 5 days until the market has 3 delivered orders.
    Then use the rounded average gap between the last 3 delivered
    order dates (pending/unverified orders are not passed in).
    """
    if default_days is None:
        default_days = getattr(
            settings, "MARKET_STATUS_DEFAULT_REFRESH_DAYS", DEFAULT_REFRESH_DAYS
        )
    dated = sorted(dt for dt in created_at_list if dt is not None)
    if len(dated) < MIN_DELIVERED_FOR_CADENCE:
        return max(1, int(default_days))

    recent = dated[-MIN_DELIVERED_FOR_CADENCE:]
    gaps = []
    for previous, current in zip(recent, recent[1:]):
        previous_day = _as_local_date(previous)
        current_day = _as_local_date(current)
        gaps.append((current_day - previous_day).days)

    if not gaps:
        return max(1, int(default_days))
    average = sum(gaps) / len(gaps)
    return max(1, int(round(average)))


def _anchor_at(last_delivered_at, last_created_at, status_updated_at):
    return last_delivered_at or last_created_at or status_updated_at


def market_is_due_for_possible(anchor, interval_days, now):
    if anchor is None:
        return False
    return now >= anchor + timedelta(days=interval_days)


@transaction.atomic
def refresh_available_markets_to_possible(now=None):
    """
    Flip AVAILABLE -> POSSIBLE (and color) after the market's order cadence.

    Skips WAITING/PENDING and any market that still has an unverified or
    approved open order. Interval uses DELIVERED orders only.
    """
    now = now or timezone.now()
    default_days = getattr(
        settings, "MARKET_STATUS_DEFAULT_REFRESH_DAYS", DEFAULT_REFRESH_DAYS
    )

    open_market_ids = Order.objects.filter(
        status__in=OPEN_ORDER_STATUSES
    ).values("market_id")

    candidate_ids = list(
        Market.objects.filter(statuses__status=SOURCE_STATUS)
        .exclude(id__in=open_market_ids)
        .order_by("id")
        .values_list("id", flat=True)
    )
    if not candidate_ids:
        return {"checked": 0, "updated": 0, "skipped": 0}

    markets = list(
        Market.objects.select_for_update(skip_locked=True)
        .filter(id__in=candidate_ids)
        .order_by("id")
    )
    if not markets:
        return {"checked": 0, "updated": 0, "skipped": 0}

    locked_ids = [market.id for market in markets]
    status_by_market = {
        row.market_id: row
        for row in MarketStatus.objects.select_for_update()
        .filter(market_id__in=locked_ids)
        .order_by("market_id")
    }

    still_open = set(
        Order.objects.filter(
            market_id__in=locked_ids,
            status__in=OPEN_ORDER_STATUSES,
        ).values_list("market_id", flat=True)
    )

    delivered_by_market = defaultdict(list)
    delivered_rows = (
        Order.objects.filter(market_id__in=locked_ids, status="DELIVERED")
        .order_by("market_id", "-created_at")
        .values_list("market_id", "created_at", "delivered_at")
    )
    for market_id, created_at, delivered_at in delivered_rows:
        bucket = delivered_by_market[market_id]
        if len(bucket) < MIN_DELIVERED_FOR_CADENCE:
            bucket.append((created_at, delivered_at))

    to_update = []
    skipped = 0
    color = status_color_for(TARGET_STATUS)

    for market in markets:
        status_obj = status_by_market.get(market.id)
        if status_obj is None or status_obj.status != SOURCE_STATUS:
            skipped += 1
            continue
        if market.id in still_open:
            skipped += 1
            continue

        recent = delivered_by_market.get(market.id, [])
        created_dates = [item[0] for item in recent]
        interval_days = cadence_interval_days(
            created_dates, default_days=default_days
        )
        newest = recent[0] if recent else (None, None)
        last_created_at, last_delivered_at = newest
        anchor = _anchor_at(
            last_delivered_at, last_created_at, status_obj.updated_at
        )
        if not market_is_due_for_possible(anchor, interval_days, now):
            continue

        status_obj.status = TARGET_STATUS
        status_obj.color_code = color
        to_update.append(status_obj)

    if to_update:
        MarketStatus.objects.bulk_update(to_update, ["status", "color_code"])

    return {
        "checked": len(markets),
        "updated": len(to_update),
        "skipped": skipped,
    }
