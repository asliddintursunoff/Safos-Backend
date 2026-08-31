from rest_framework import serializers

from django.utils import timezone
from django.db import transaction

from apps.orders.models import Order
from apps.common.choices import ORDER_STATUS_CHOICES
from apps.users.api.serializers import UserBaseReadSerializer
from apps.orders.services.transaction_from_market_credit import (
    pay_from_market_credit,
    refund_market_credit_from_order,
)

class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    
class CreateOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only = True)
    market_id = serializers.UUIDField()
    items =  CreateOrderItemSerializer(many = True,write_only = True)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=3, read_only=True)
    total_price_with_discount = serializers.DecimalField(max_digits=20, decimal_places=3, read_only=True)
 
    
ALLOWED_UPDATE_STATUSES = ["APPROVED","PENDING"]

def can_update(user,instance):
    # if user.role_type == 'ADMIN':
    #     return True
    if instance.status in ALLOWED_UPDATE_STATUSES:
        return True
    return False

class UpdateOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only = True)
    items =  CreateOrderItemSerializer(many = True,write_only = True)
    
    def validate(self, attrs):
        request = self.context["request"]
        if not can_update(request.user,self.instance):
            raise serializers.ValidationError("Faqat Tasdiqlangan yoki Tasdiqlanishi kutilayotgan buyurtmani o'zgartira olasiz!")
        
        return super().validate(attrs)
    
    
def person_name(user):
    if not user:
        return None
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or None


class ListReadOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    market_id = serializers.UUIDField(source = "market.id")
    markent_name = serializers.CharField(source = 'market.name')
    status = serializers.CharField(source="get_status_display", read_only=True)
    status_code = serializers.CharField(source="status")
    ordered_by_name = serializers.SerializerMethodField()
    ordered_by_first_name = serializers.SerializerMethodField()
    ordered_by_last_name = serializers.SerializerMethodField()
    delivered_by_name = serializers.SerializerMethodField()
    delivered_by_first_name = serializers.SerializerMethodField()
    delivered_by_last_name = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=20,decimal_places=3)
    total_price_with_discount = serializers.DecimalField(max_digits=20,decimal_places=3)
    is_debt_paid = serializers.BooleanField()
    created_date = serializers.DateTimeField(source="created_at", format="%d-%m-%Y")
    created_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M')

    def get_ordered_by_name(self, obj):
        return person_name(getattr(obj, "ordered_by", None))

    def get_ordered_by_first_name(self, obj):
        user = getattr(obj, "ordered_by", None)
        return (user.first_name or "") if user else None

    def get_ordered_by_last_name(self, obj):
        user = getattr(obj, "ordered_by", None)
        return (user.last_name or "") if user else None

    def get_delivered_by_name(self, obj):
        return person_name(getattr(obj, "delivered_by", None))

    def get_delivered_by_first_name(self, obj):
        user = getattr(obj, "delivered_by", None)
        return (user.first_name or "") if user else None

    def get_delivered_by_last_name(self, obj):
        user = getattr(obj, "delivered_by", None)
        return (user.last_name or "") if user else None
    
    
class OrderItemDetailSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(source="product.id")
    product_name = serializers.CharField(source = 'product.name')
    product_unit = serializers.SerializerMethodField()
    product_value = serializers.DecimalField(max_digits=10,decimal_places=2,source = 'product.value')
    product_price = serializers.DecimalField(max_digits=15,decimal_places=3,source = 'product.price')
    quantity  = serializers.IntegerField()
    total_price = serializers.SerializerMethodField()
    
    def get_product_unit(self, obj):
        return obj.product.get_unit_display()

    def get_total_price(self,obj):
        return obj.quantity*obj.product.price
    
class OrderDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    market_id = serializers.UUIDField(source="market.id")
    market_name = serializers.CharField(source = 'market.name')
    market_description = serializers.CharField(source="market.description", allow_blank=True, allow_null=True)
    market_discount_percentage = serializers.DecimalField(max_digits=5,decimal_places=2,source = 'market.discount_percentage')
    market_location_latitude = serializers.SerializerMethodField()
    market_location_longitude = serializers.SerializerMethodField()
    market_owner = UserBaseReadSerializer(source="market.owner", allow_null=True)
    ordered_by = UserBaseReadSerializer(allow_null=True)
    delivered_by = UserBaseReadSerializer(allow_null=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    status_code = serializers.CharField(source="status")
    is_debt_paid = serializers.BooleanField()
    total_price = serializers.DecimalField(max_digits=20,decimal_places=3)
    total_price_with_discount = serializers.DecimalField(max_digits=20,decimal_places=3)
    created_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M')
    approved_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M', allow_null=True)
    delivered_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M')
    cancelled_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M')
    
    items = OrderItemDetailSerializer(many = True)
    def get_market_location_latitude(self, obj):
        return obj.market.location.y if obj.market and obj.market.location else None
    
    def get_market_location_longitude(self, obj):
        return obj.market.location.x if obj.market and obj.market.location else None
        


STATUS_TRANSITIONS = {
    "DELIVERER": {
        "PENDING": ["APPROVED", "REJECTED", "DELIVERED", "CANCELLED"],
        "APPROVED": ["PENDING", "DELIVERED", "CANCELLED"],
        "DELIVERED": ["CANCELLED", "APPROVED"],
        "CANCELLED": ["DELIVERED", "APPROVED", "PENDING"],
        "REJECTED": ["PENDING", "APPROVED"],
    },
    "AGENT": {},
    "CUSTOMER": {},
}



def can_transition(user, instance, new_status):
    role = getattr(user, "role_type", None)
    current = getattr(instance, "status", None)
    labels = {label: code for code, label in ORDER_STATUS_CHOICES.items()}
    current = labels.get(current, current)
    new_status = labels.get(new_status, new_status)
    if role == "ADMIN":
        return True
    if role == "DELIVERER" and current in ("PENDING", "APPROVED") and new_status in ("PENDING", "APPROVED"):
        return True
    transitions = STATUS_TRANSITIONS.get(role, {})
    allowed = transitions.get(current, [])
    return new_status in allowed
            

class InvalidStatusTransition(Exception):
    pass
def change_order_status_service(instance:Order,status,user):
    
    if instance.status == status:
        raise InvalidStatusTransition(f"Buyurtma allaqachon '{instance.get_status_display()}' holatda turibdi")
    
    
    if status == 'DELIVERED':
        instance.delivered_by = user
        instance.market.statuses.color_code = 'AVAILABLE'
        instance.market.statuses.status = 'AVAILABLE'
        instance.delivered_at = timezone.localtime()
        instance.cancelled_at = None
        pay_from_market_credit(instance)
        
    if status == 'APPROVED':
        instance.approved_at = timezone.localtime()
        instance.delivered_at = None
        instance.cancelled_at = None
        instance.delivered_by = None
        instance.market.statuses.last_order = instance
        instance.market.statuses.color_code = 'WAITING'
        instance.market.statuses.status = 'WAITING'
    if status == 'CANCELLED':
        instance.delivered_at = None
        instance.cancelled_at = timezone.localtime()
        instance.delivered_by = None
        instance.market.statuses.color_code = 'NOT_NEEDED'
        instance.market.statuses.status = 'NOT_NEEDED'
        refund_market_credit_from_order(instance)
               
    if status == 'REJECTED':
        instance.approved_at = None
        instance.delivered_at = None
        instance.cancelled_at = None
        instance.delivered_by = None
        instance.market.statuses.color_code = 'NOT_NEEDED'
        instance.market.statuses.status = 'NOT_NEEDED'
        refund_market_credit_from_order(instance) 
    if status == 'PENDING':
        instance.approved_at = None
        instance.delivered_at = None
        instance.cancelled_at = None
        instance.delivered_by = None
        instance.market.statuses.color_code = 'PENDING'
        instance.market.statuses.status = 'PENDING' 
        
    
    instance.status = status
    instance.market.statuses.save()
    instance.market.save()
    instance.save()
    return instance


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ORDER_STATUS_CHOICES,help_text=(
            "Allowed values: APPROVED, REJECTED, PENDING, "
            "CANCELLED, DELIVERED, DELIVERING"
        ))
    
    def validate_status(self,value):
        request = self.context["request"]
        role = getattr(request.user, "role_type", None)
        current = getattr(self.instance, "status", None)
        if role in ("ADMIN", "DELIVERER") and current == "APPROVED" and value == "PENDING":
            return value
        if role in ("ADMIN", "DELIVERER") and current == "PENDING" and value == "APPROVED":
            return value
        if not can_transition(request.user, self.instance, value):
            raise serializers.ValidationError("Siz bu buyurtmani o'zgarita olmaysiz!")
        return value
    
    @transaction.atomic 
    def update(self, instance, validated_data):
        validated_data['status']
        request = self.context["request"]
        
        instance = (
            Order.objects
            .select_for_update()
            .get(pk=instance.pk)
        )
        try:
            instance = change_order_status_service(instance,validated_data['status'],request.user)
            return instance
        except InvalidStatusTransition as e:
            raise serializers.ValidationError(str(e))
        
