from django.contrib.gis.db import models

from apps.common.models import BaseModel
from apps.common.choices import ORDER_STATUS_CHOICES

class Order(BaseModel):
    market = models.ForeignKey("markets.Market", on_delete=models.CASCADE, related_name='orders')
    ordered_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, related_name='ordered_by_orders')
    delivered_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True,blank=True, related_name='delivered_by_orders')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="PENDING")
    total_price = models.DecimalField(max_digits=20, decimal_places=3, default=0.00)
    total_price_with_discount = models.DecimalField(max_digits=20, decimal_places=3, default=0.00)
    is_debt_paid = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.id}"
    
class OrderItem(BaseModel):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"OrderItem {self.id} for Order {self.order.id}"
    
    
class OrderItemConribution(BaseModel):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name='items_contribution')
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True, related_name='order_items_contribution')
    quantity = models.PositiveIntegerField(default=0)
    peak_quantity = models.PositiveIntegerField(default=0)  # Tracks historical max contribution
    ordered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_contributions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product', 'ordered_by'],
                name='unique_order_product_contributor',
            )
        ]

    def __str__(self):
        return f"OrderItem {self.id} for Order {self.order.id}"