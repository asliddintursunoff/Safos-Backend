from django.contrib.gis.db import models

from apps.common.models import BaseModel

class Payment(BaseModel):
    amount = models.DecimalField(max_digits=20, decimal_places=3)
    market = models.ForeignKey("markets.Market", on_delete=models.SET_NULL, null=True, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    taken_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, related_name='taken_payments')
    def __str__(self):
        return f"Payment {self.id} for Order {self.id}"
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), 
                name="amount_must_be_greater_than_zero"
            )
        ]
        
class PaymentAllocation(BaseModel):
    payment = models.ForeignKey("transactions.Payment", on_delete=models.CASCADE,null=True,blank=True, related_name='allocations')
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name='payments')
    allocated_amount = models.DecimalField(max_digits=20, decimal_places=3)
    payment_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"PaymentAllocation {self.id} for Payment and Order {self.order.id}"
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(allocated_amount__gt=0), 
                name="allocated_amount_must_be_greater_than_zero"
            )
        ]