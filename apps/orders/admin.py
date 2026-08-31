import nested_admin
from django.contrib import admin

from .models import (
    Order,
    OrderItem,
    OrderItemConribution
    
)





class OrderItemInline(nested_admin.NestedTabularInline):
    model = OrderItem
    extra = 0

class OrderItemContribution(nested_admin.NestedTabularInline):
    model = OrderItemConribution
    extra = 0

@admin.register(Order)
class OrderAdmin(nested_admin.NestedModelAdmin):
    inlines = [
        OrderItemInline,
        OrderItemContribution
    ]