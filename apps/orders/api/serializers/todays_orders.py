from rest_framework import serializers
from rest_framework.serializers import Serializer, DecimalField as SerDecimalField, UUIDField, CharField
from apps.common.choices import PRODUCT_UNIT_CHOICES

class DeliveringMarketOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    market_id = serializers.UUIDField(source = "market.id")
    markent_name = serializers.CharField(source = 'market.name')
    market_location_latitude = serializers.SerializerMethodField()
    market_location_longitude = serializers.SerializerMethodField()
    market_status = serializers.SerializerMethodField()
    market_status_code = serializers.SerializerMethodField()
    market_status_color = serializers.SerializerMethodField()
    market_image = serializers.SerializerMethodField()

    def get_market_location_latitude(self, obj):
            return obj.market.location.y if obj.market and obj.market.location else None
        
    def get_market_location_longitude(self, obj):
        return obj.market.location.x if obj.market and obj.market.location else None

    def _statuses(self, obj):
        market = getattr(obj, "market", None)
        return getattr(market, "statuses", None) if market else None

    def get_market_status(self, obj):
        statuses = self._statuses(obj)
        if not statuses:
            return None
        return statuses.get_status_display()

    def get_market_status_code(self, obj):
        statuses = self._statuses(obj)
        return getattr(statuses, "status", None) if statuses else None

    def get_market_status_color(self, obj):
        statuses = self._statuses(obj)
        if not statuses:
            return None
        return statuses.get_color_code_display()

    def get_market_image(self, obj):
        market = getattr(obj, "market", None)
        if not market or not getattr(market, "image", None):
            return None
        request = self.context.get("request")
        url = market.image.url
        if request:
            return request.build_absolute_uri(url)
        return url
        
    
    
class ProductOrderQuantitySerializer(serializers.Serializer):
    product_name = serializers.CharField()
    unit = serializers.ChoiceField(choices=PRODUCT_UNIT_CHOICES)
    value = serializers.DecimalField(max_digits=10,decimal_places=2)
    total_price = serializers.DecimalField(max_digits=20,decimal_places=3)
    total_quantity = serializers.IntegerField()
    
class DeliveringTotalOrdersSerializer(serializers.Serializer):
    total_count_of_orders = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=20,decimal_places=3)
    total_price_with_discount = serializers.DecimalField(max_digits=20,decimal_places=3)
    counts_of_each_product = ProductOrderQuantitySerializer(many = True)
    
class MyOrdersTotalPriceSerializer(Serializer):
    total = SerDecimalField(max_digits=20, decimal_places=3)
    delivered = SerDecimalField(max_digits=20, decimal_places=3)


class TotalPriceByAllUsersOrderSerializer(Serializer):
    user_id = UUIDField()
    user_first_name = CharField()
    user_last_name = CharField()
    total = SerDecimalField(max_digits=20, decimal_places=3)
    delivered = SerDecimalField(max_digits=20, decimal_places=3)