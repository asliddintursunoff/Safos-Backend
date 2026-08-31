from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.markets.models import Market, MarketStatus
from apps.orders.models import Order
from apps.transactions.models import PaymentAllocation
from apps.users.models import User


class MarketAnalyticsAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone_number="+998901111111",
            password="pass",
            role_type="ADMIN",
        )
        self.agent = User.objects.create_user(
            phone_number="+998902222222",
            password="pass",
            role_type="AGENT",
        )
        self.client.force_authenticate(self.admin)

        self.alpha = self._market("Alpha", "AVAILABLE")
        self.beta = self._market("Beta", "AVAILABLE")
        self.gamma = self._market("Gamma", "NOT_NEEDED")
        Market.objects.filter(pk=self.gamma.pk).update(
            created_at=timezone.now() - timedelta(days=40)
        )
        self.gamma.refresh_from_db()

        self._order(self.alpha, "100.000", days_ago=20, allocated="40.000")
        self._order(self.alpha, "200.000", days_ago=2, allocated="200.000")
        self._order(self.beta, "50.000", days_ago=20, allocated="50.000")
        self._order(
            self.beta,
            "999.000",
            days_ago=1,
            status="CANCELLED",
            allocated=None,
        )

    def _market(self, name, status, credit="0.000"):
        market = Market.objects.create(
            name=name,
            credit_amount=Decimal(credit),
        )
        MarketStatus.objects.create(
            market=market,
            status=status,
            color_code=status,
        )
        return market

    def _order(
        self,
        market,
        amount,
        days_ago=0,
        status="DELIVERED",
        allocated=None,
        hours_offset=0,
    ):
        when = timezone.now() - timedelta(days=days_ago, hours=hours_offset)
        paid = (
            status == "DELIVERED"
            and allocated is not None
            and Decimal(allocated) >= Decimal(amount)
        )
        order = Order.objects.create(
            market=market,
            status=status,
            total_price=Decimal(amount),
            total_price_with_discount=Decimal(amount),
            is_debt_paid=paid,
            ordered_by=self.admin,
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=when,
            delivered_at=when if status == "DELIVERED" else None,
        )
        order.refresh_from_db()
        if allocated is not None:
            PaymentAllocation.objects.create(
                order=order,
                allocated_amount=Decimal(allocated),
            )
        return order

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("market-analytics-volume"))
        self.assertIn(response.status_code, (401, 403))

    def test_non_admin_is_rejected(self):
        self.client.force_authenticate(self.agent)
        response = self.client.get(reverse("market-analytics-volume"))
        self.assertEqual(response.status_code, 403)

    def test_deliverer_can_access_activity_and_summary(self):
        deliverer = User.objects.create_user(
            phone_number="+998903333333",
            password="secret123",
            role_type="DELIVERER",
        )
        self.client.force_authenticate(deliverer)
        activity = self.client.get(reverse("market-analytics-activity"))
        self.assertEqual(activity.status_code, 200)
        summary = self.client.get(reverse("market-analytics-summary"))
        self.assertEqual(summary.status_code, 200)

    def test_volume_all_time_highest_first_excludes_cancelled(self):
        response = self.client.get(reverse("market-analytics-volume"))
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        names = [row["name"] for row in results]
        self.assertEqual(names[0], "Alpha")
        alpha = results[0]
        self.assertEqual(Decimal(alpha["ordered_amount"]), Decimal("300.000"))
        self.assertEqual(alpha["order_count"], 2)
        self.assertEqual(Decimal(alpha["total_debt"]), Decimal("60.000"))
        beta = next(row for row in results if row["name"] == "Beta")
        self.assertEqual(Decimal(beta["ordered_amount"]), Decimal("50.000"))
        self.assertEqual(Decimal(beta["total_debt"]), Decimal("0.000"))

    def test_volume_date_range_does_not_change_debt(self):
        end = timezone.localdate()
        start = end - timedelta(days=5)
        response = self.client.get(
            reverse("market-analytics-volume"),
            {
                "start_date": start.strftime("%d-%m-%Y"),
                "end_date": end.strftime("%d-%m-%Y"),
            },
        )
        self.assertEqual(response.status_code, 200)
        alpha = next(
            row for row in response.data["results"] if row["name"] == "Alpha"
        )
        self.assertEqual(Decimal(alpha["ordered_amount"]), Decimal("200.000"))
        self.assertEqual(alpha["order_count"], 1)
        self.assertEqual(Decimal(alpha["total_debt"]), Decimal("60.000"))

    def test_has_debt_filter_ignores_date_range(self):
        end = timezone.localdate()
        start = end - timedelta(days=5)
        response = self.client.get(
            reverse("market-analytics-volume"),
            {
                "start_date": start.strftime("%d-%m-%Y"),
                "end_date": end.strftime("%d-%m-%Y"),
                "has_debt": "true",
            },
        )
        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["Alpha"])
        self.assertEqual(
            Decimal(response.data["results"][0]["total_debt"]),
            Decimal("60.000"),
        )

    def test_volume_ordering_lowest_first(self):
        response = self.client.get(
            reverse("market-analytics-volume"),
            {"ordering": "ordered_amount"},
        )
        amounts = [
            Decimal(row["ordered_amount"]) for row in response.data["results"]
        ]
        self.assertEqual(amounts, sorted(amounts))

    def test_debt_orders_are_current_unpaid_only(self):
        response = self.client.get(
            reverse("market-analytics-debts", kwargs={"id": self.alpha.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        row = response.data["results"][0]
        self.assertEqual(Decimal(row["remaining_debt"]), Decimal("60.000"))
        self.assertEqual(Decimal(row["allocated_amount"]), Decimal("40.000"))
        self.assertFalse(row["is_debt_paid"])

    def test_activity_frequency_and_inactive_filter(self):
        regular = self._market("Regular", "AVAILABLE")
        self._order(regular, "10.000", days_ago=6, allocated="10.000")
        self._order(
            regular,
            "10.000",
            days_ago=3,
            allocated="10.000",
            hours_offset=1,
        )

        response = self.client.get(
            reverse("market-analytics-activity"),
            {"search": "Regular"},
        )
        self.assertEqual(response.status_code, 200)
        row = response.data["results"][0]
        self.assertEqual(row["frequency_code"], "EVERY_3_DAYS")
        self.assertAlmostEqual(row["avg_days_between_orders"], 3.0, delta=0.2)

        inactive = self.client.get(
            reverse("market-analytics-activity"),
            {"inactive_days": 7},
        )
        names = {row["name"] for row in inactive.data["results"]}
        self.assertIn("Gamma", names)
        self.assertIn("Beta", names)
        self.assertNotIn("Alpha", names)
        self.assertNotIn("Regular", names)

    def test_activity_ordering_lowest_days_first(self):
        response = self.client.get(
            reverse("market-analytics-activity"),
            {"ordering": "days_since_last_order"},
        )
        days = [
            row["days_since_last_order"] for row in response.data["results"]
        ]
        self.assertEqual(days, sorted(days))

    def test_bulk_status_updates_selected_and_skips_active(self):
        waiting = self._market("WaitingShop", "WAITING")
        self._order(waiting, "15.000", days_ago=1, status="APPROVED")

        response = self.client.put(
            reverse("market-analytics-bulk-status"),
            {
                "market_ids": [str(self.gamma.id), str(waiting.id)],
                "status": "POSSIBLE",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated_count"], 1)
        self.assertEqual(len(response.data["skipped"]), 1)
        self.gamma.statuses.refresh_from_db()
        waiting.statuses.refresh_from_db()
        self.assertEqual(self.gamma.statuses.status, "POSSIBLE")
        self.assertEqual(self.gamma.statuses.color_code, "POSSIBLE")
        self.assertEqual(waiting.statuses.status, "WAITING")

    def test_single_market_status_and_detail(self):
        response = self.client.put(
            reverse("market-analytics-status", kwargs={"id": self.gamma.id}),
            {"status": "AVAILABLE"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.gamma.statuses.refresh_from_db()
        self.assertEqual(self.gamma.statuses.status, "AVAILABLE")

        detail = self.client.get(
            reverse("market-analytics-detail", kwargs={"id": self.alpha.id})
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(detail.data["total_debt"]), Decimal("60.000"))
        self.assertEqual(detail.data["unpaid_order_count"], 1)
        self.assertEqual(Decimal(detail.data["ordered_amount"]), Decimal("300.000"))

    def test_summary_includes_debt_and_inactive(self):
        response = self.client.get(reverse("market-analytics-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["markets_with_debt"], 1)
        self.assertEqual(Decimal(response.data["total_debt"]), Decimal("60.000"))
        self.assertGreaterEqual(response.data["never_ordered"], 1)
        self.assertIn("AVAILABLE", response.data["status_counts"])


class MarketStatusRefreshTests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            phone_number="+998903333333",
            password="pass",
            role_type="ADMIN",
        )

    def _market(self, name, status="AVAILABLE"):
        market = Market.objects.create(name=name)
        MarketStatus.objects.create(
            market=market,
            status=status,
            color_code=status,
        )
        return market

    def _delivered(self, market, days_ago, status="DELIVERED"):
        when = self.now - timedelta(days=days_ago)
        order = Order.objects.create(
            market=market,
            status=status,
            total_price=Decimal("10.000"),
            total_price_with_discount=Decimal("10.000"),
            ordered_by=self.user,
            is_debt_paid=status == "DELIVERED",
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=when,
            delivered_at=when if status == "DELIVERED" else None,
        )
        return order

    def test_default_five_days_without_three_delivered_orders(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        too_soon = self._market("TooSoon")
        due = self._market("DueDefault")
        self._delivered(too_soon, 4)
        self._delivered(due, 5)

        result = refresh_available_markets_to_possible(now=self.now)
        too_soon.statuses.refresh_from_db()
        due.statuses.refresh_from_db()

        self.assertEqual(too_soon.statuses.status, "AVAILABLE")
        self.assertEqual(due.statuses.status, "POSSIBLE")
        self.assertEqual(due.statuses.color_code, "POSSIBLE")
        self.assertEqual(result["updated"], 1)

    def test_cadence_one_day_after_three_delivered_orders(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        market = self._market("Daily")
        self._delivered(market, 3)
        self._delivered(market, 2)
        self._delivered(market, 1)
        self._delivered(market, 0, status="REJECTED")

        refresh_available_markets_to_possible(now=self.now)
        market.statuses.refresh_from_db()
        self.assertEqual(market.statuses.status, "POSSIBLE")
        self.assertEqual(market.statuses.color_code, "POSSIBLE")

    def test_cadence_three_days_is_not_due_early(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        market = self._market("EveryThree")
        self._delivered(market, 8)
        self._delivered(market, 5)
        self._delivered(market, 2)

        refresh_available_markets_to_possible(now=self.now)
        market.statuses.refresh_from_db()
        self.assertEqual(market.statuses.status, "AVAILABLE")

    def test_cadence_ten_days_flips_on_schedule(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        market = self._market("EveryTen")
        self._delivered(market, 30)
        self._delivered(market, 20)
        self._delivered(market, 10)

        refresh_available_markets_to_possible(now=self.now)
        market.statuses.refresh_from_db()
        self.assertEqual(market.statuses.status, "POSSIBLE")
        self.assertEqual(market.statuses.color_code, "POSSIBLE")

    def test_skips_active_and_pending_markets(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        waiting = self._market("Waiting", "WAITING")
        available_open = self._market("OpenOrder")
        self._delivered(waiting, 10)
        self._delivered(available_open, 10)
        self._delivered(available_open, 1, status="APPROVED")

        refresh_available_markets_to_possible(now=self.now)
        waiting.statuses.refresh_from_db()
        available_open.statuses.refresh_from_db()
        self.assertEqual(waiting.statuses.status, "WAITING")
        self.assertEqual(available_open.statuses.status, "AVAILABLE")

    def test_unverified_orders_do_not_shorten_default_interval(self):
        from apps.markets.services.status_refresh import (
            refresh_available_markets_to_possible,
        )

        market = self._market("UnverifiedNoise")
        self._delivered(market, 2)
        self._delivered(market, 1)
        self._delivered(market, 0, status="REJECTED")

        refresh_available_markets_to_possible(now=self.now)
        market.statuses.refresh_from_db()
        self.assertEqual(market.statuses.status, "AVAILABLE")


class MarketCreatePermissionTests(APITestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            phone_number="+998901000010",
            password="pass",
            role_type="AGENT",
        )
        self.customer = User.objects.create_user(
            phone_number="+998901000011",
            password=None,
            role_type="CUSTOMER",
        )

    def test_agent_can_create_market_without_location(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post(
            "/api/markets/",
            {"name": "Yangi do'kon"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        market = Market.objects.get(name="Yangi do'kon")
        self.assertIsNone(market.location)
        self.assertEqual(market.created_by_id, self.agent.id)

    def test_customer_can_add_only_one_market(self):
        self.client.force_authenticate(self.customer)
        first = self.client.post(
            "/api/markets/",
            {"name": "Mening do'konim"},
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(
            Market.objects.get(id=first.data["id"]).owner_id, self.customer.id
        )
        second = self.client.post(
            "/api/markets/",
            {"name": "Ikkinchi"},
            format="json",
        )
        self.assertEqual(second.status_code, 400)

