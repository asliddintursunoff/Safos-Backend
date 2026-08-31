from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.markets.models import Market
from apps.orders.models import Order
from apps.transactions.models import PaymentAllocation

ZERO = Decimal("0.000")
CENT = Decimal("0.001")


def _as_money(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(value).quantize(CENT)


def _allocated_total(order: Order) -> Decimal:
    total = order.payments.aggregate(total=Sum("allocated_amount"))["total"]
    return _as_money(total)


def _sync_cached_market(order: Order, market: Market) -> None:
    cached = getattr(order, "market", None)
    if cached is not None and cached.pk == market.pk:
        cached.credit_amount = market.credit_amount


def _refund_credit_allocations(order: Order, market: Market, amount: Decimal) -> Decimal:
    """Return up to `amount` of prepaid credit (payment=None) to the market."""
    if amount <= ZERO:
        return ZERO

    remaining = amount
    refunded = ZERO
    credit_allocs = (
        PaymentAllocation.objects.select_for_update()
        .filter(order=order, payment__isnull=True)
        .order_by("-payment_date", "-id")
    )

    for alloc in credit_allocs:
        if remaining <= ZERO:
            break
        if alloc.allocated_amount <= remaining:
            remaining -= alloc.allocated_amount
            refunded += alloc.allocated_amount
            alloc.delete()
        else:
            alloc.allocated_amount -= remaining
            refunded += remaining
            alloc.save(update_fields=["allocated_amount"])
            remaining = ZERO

    if refunded > ZERO:
        market.credit_amount = _as_money(market.credit_amount) + refunded
    return refunded


@transaction.atomic
def pay_from_market_credit(order: Order) -> Order:
    """
    Apply market.credit_amount to this order.

    - credit < remaining due: allocate all credit, is_debt_paid=False, credit=0
    - credit == remaining due: allocate all credit, is_debt_paid=True, credit=0
    - credit > remaining due: allocate remaining due, is_debt_paid=True, leftover stays on market

    Idempotent: existing allocations are subtracted from the due amount first.
    If the order total shrank below what was prepaid from credit, the extra
    is returned to the market.
    """
    market = Market.objects.select_for_update().get(pk=order.market_id)
    due = _as_money(order.total_price_with_discount)
    remaining_due = due - _allocated_total(order)

    if remaining_due < ZERO:
        _refund_credit_allocations(order, market, -remaining_due)
        remaining_due = due - _allocated_total(order)
        if remaining_due < ZERO:
            remaining_due = ZERO

    credit = _as_money(market.credit_amount)
    if remaining_due > ZERO and credit > ZERO:
        amount = min(credit, remaining_due)
        market.credit_amount = credit - amount
        remaining_due -= amount
        PaymentAllocation.objects.create(
            order=order,
            allocated_amount=amount,
            payment=None,
        )
    elif credit < ZERO:
        market.credit_amount = ZERO

    order.is_debt_paid = remaining_due <= ZERO
    market.save(update_fields=["credit_amount"])
    order.save(update_fields=["is_debt_paid"])
    _sync_cached_market(order, market)
    return order


def _credit_allocated_total(order: Order) -> Decimal:
    total = PaymentAllocation.objects.filter(
        order=order, payment__isnull=True
    ).aggregate(total=Sum("allocated_amount"))["total"]
    return _as_money(total)


@transaction.atomic
def refund_market_credit_from_order(order: Order) -> Order:
    """Move prepaid credit allocations on this order back to market.credit_amount."""
    market = Market.objects.select_for_update().get(pk=order.market_id)
    refunded = _refund_credit_allocations(order, market, _credit_allocated_total(order))
    if refunded > ZERO:
        market.save(update_fields=["credit_amount"])
        _sync_cached_market(order, market)

    remaining_due = _as_money(order.total_price_with_discount) - _allocated_total(order)
    order.is_debt_paid = remaining_due <= ZERO
    order.save(update_fields=["is_debt_paid"])
    return order
