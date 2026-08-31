from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase

from apps.markets.models import Market, MarketStatus
from apps.orders.models import Order
from apps.users.models import User
from apps.orders.services.transaction_from_market_credit import (
    pay_from_market_credit,
    refund_market_credit_from_order,
)
from apps.transactions.models import PaymentAllocation


class PayFromMarketCreditTests(TestCase):
    def _order(self, credit, total):
        market = Market.objects.create(name="Test market", credit_amount=Decimal(credit))
        order = Order.objects.create(
            market=market,
            total_price=Decimal(total),
            total_price_with_discount=Decimal(total),
        )
        return market, order

    def test_credit_less_than_order_partial_allocation(self):
        market, order = self._order("40.000", "100.000")
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()
        alloc = PaymentAllocation.objects.get(order=order)

        self.assertFalse(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("0.000"))
        self.assertEqual(alloc.allocated_amount, Decimal("40.000"))
        self.assertIsNone(alloc.payment_id)

    def test_credit_equal_to_order_fully_paid(self):
        market, order = self._order("100.000", "100.000")
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()
        alloc = PaymentAllocation.objects.get(order=order)

        self.assertTrue(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("0.000"))
        self.assertEqual(alloc.allocated_amount, Decimal("100.000"))

    def test_credit_more_than_order_leftover_stays_on_market(self):
        market, order = self._order("150.000", "100.000")
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()
        alloc = PaymentAllocation.objects.get(order=order)

        self.assertTrue(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("50.000"))
        self.assertEqual(alloc.allocated_amount, Decimal("100.000"))

    def test_idempotent_does_not_double_allocate_on_second_call(self):
        market, order = self._order("150.000", "100.000")
        pay_from_market_credit(order)
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()

        self.assertTrue(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("50.000"))
        self.assertEqual(PaymentAllocation.objects.filter(order=order).count(), 1)

    def test_shrinking_order_refunds_extra_credit(self):
        market, order = self._order("150.000", "100.000")
        pay_from_market_credit(order)

        order.total_price_with_discount = Decimal("70.000")
        order.save(update_fields=["total_price_with_discount"])
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()
        alloc = PaymentAllocation.objects.get(order=order)

        self.assertTrue(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("80.000"))
        self.assertEqual(alloc.allocated_amount, Decimal("70.000"))

    def test_growing_order_uses_remaining_credit(self):
        market, order = self._order("150.000", "100.000")
        pay_from_market_credit(order)

        order.total_price_with_discount = Decimal("180.000")
        order.save(update_fields=["total_price_with_discount"])
        pay_from_market_credit(order)

        market.refresh_from_db()
        order.refresh_from_db()
        total_allocated = sum(
            a.allocated_amount for a in PaymentAllocation.objects.filter(order=order)
        )

        self.assertFalse(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("0.000"))
        self.assertEqual(total_allocated, Decimal("150.000"))

    def test_refund_returns_credit_to_market(self):
        market, order = self._order("150.000", "100.000")
        pay_from_market_credit(order)
        refund_market_credit_from_order(order)

        market.refresh_from_db()
        order.refresh_from_db()

        self.assertFalse(order.is_debt_paid)
        self.assertEqual(market.credit_amount, Decimal("150.000"))
        self.assertEqual(
            PaymentAllocation.objects.filter(order=order, payment__isnull=True).count(),
            0,
        )


class AgentOrderPermissionTests(APITestCase):
    def setUp(self):
        self.agent_a = User.objects.create_user(
            phone_number="+998901000021",
            password="pass",
            role_type="AGENT",
        )
        self.agent_b = User.objects.create_user(
            phone_number="+998901000022",
            password="pass",
            role_type="AGENT",
        )
        self.market = Market.objects.create(name="Agent shop")
        MarketStatus.objects.create(
            market=self.market, status="PENDING", color_code="PENDING"
        )
        self.order = Order.objects.create(
            market=self.market,
            ordered_by=self.agent_a,
            status="PENDING",
            total_price=Decimal("10.000"),
            total_price_with_discount=Decimal("10.000"),
        )

    def test_other_agent_can_update_but_not_delete(self):
        self.client.force_authenticate(self.agent_b)
        update = self.client.put(
            f"/api/orders/{self.order.id}/",
            {"items": []},
            format="json",
        )
        self.assertEqual(update.status_code, 200)

        delete = self.client.delete(f"/api/orders/{self.order.id}/")
        self.assertEqual(delete.status_code, 403)

    def test_owner_agent_can_delete_pending(self):
        self.client.force_authenticate(self.agent_a)
        delete = self.client.delete(f"/api/orders/{self.order.id}/")
        self.assertEqual(delete.status_code, 204)
