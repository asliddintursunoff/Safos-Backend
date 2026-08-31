from collections import defaultdict
from decimal import Decimal
from django.db.models import F, Sum
from apps.orders.models import OrderItem


def sync_order_items( order, user, new_items: dict):
    """new_items: {product_id: quantity}"""
    existing = (
        OrderItem.objects
        .select_for_update()
        .filter(order=order)
        .order_by("product_id", "-created_at")
    )

    by_product = defaultdict(list)
    for row in existing:
        by_product[row.product_id].append(row)

    all_product_ids = set(by_product) | set(new_items)

    for product_id in all_product_ids:
        old_qty = sum(r.quantity for r in by_product.get(product_id, []))
        new_qty = new_items.get(product_id, 0)
        diff = new_qty - old_qty

        if diff == 0:
            continue

        if diff > 0:
            row, created = OrderItem.objects.select_for_update().get_or_create(
                order=order, product_id=product_id, ordered_by=user,
                defaults={"quantity": 0},
            )
            OrderItem.objects.filter(pk=row.pk).update(quantity=F("quantity") + diff)
            continue

        # diff < 0 — LIFO: eng oxirgi qo'shgan contributordan kamaytiramiz
        remaining = -diff
        for row in by_product.get(product_id, []):
            if remaining <= 0:
                break
            deduction = min(row.quantity, remaining)
            row.quantity -= deduction
            remaining -= deduction
            if row.quantity == 0:
                row.delete()
            else:
                row.save(update_fields=["quantity"])