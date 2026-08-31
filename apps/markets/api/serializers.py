import re

from rest_framework import serializers

from django.contrib.gis.geos import Point

from apps.markets.models import Market, MarketStatus
from apps.users.models import User
from apps.users.api.serializers import UserBaseReadSerializer



OPEN_ORDER_STATUSES = ("PENDING", "APPROVED")


def _last_open_order(obj):
    statuses = getattr(obj, "statuses", None)
    order = getattr(statuses, "last_order", None) if statuses else None
    if not order or order.status not in OPEN_ORDER_STATUSES:
        return None
    return order


class MarketListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='statuses.get_status_display', read_only=True)
    status_code = serializers.CharField(source='statuses.status', read_only=True)
    status_color_code = serializers.CharField(source='statuses.get_color_code_display', read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distance_m = serializers.SerializerMethodField()
    last_order_id = serializers.SerializerMethodField()
    last_order_open = serializers.SerializerMethodField()
    last_order_agent_name = serializers.SerializerMethodField()
    last_order_agent_color = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    class Meta:
        model = Market
        fields = [
            'id', 'name', 'status', 'status_code', 'status_color_code',
            'latitude', 'longitude', 'distance_m', 'last_order_id',
            'last_order_open', 'last_order_agent_name', 'last_order_agent_color',
            'image',
        ]
    
    def get_latitude(self, obj):
        return obj.location.y if obj.location else None
    
    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_distance_m(self, obj):
        distance = getattr(obj, "distance", None)
        if distance is None:
            return None
        return round(distance.m)

    def get_last_order_id(self, obj):
        statuses = getattr(obj, "statuses", None)
        return getattr(statuses, "last_order_id", None) if statuses else None

    def get_last_order_open(self, obj):
        return _last_open_order(obj) is not None

    def get_last_order_agent_name(self, obj):
        order = _last_open_order(obj)
        agent = getattr(order, "ordered_by", None) if order else None
        if not agent:
            return None
        name = f"{agent.first_name or ''} {agent.last_name or ''}".strip()
        return name or agent.phone_number

    def get_last_order_agent_color(self, obj):
        order = _last_open_order(obj)
        agent = getattr(order, "ordered_by", None) if order else None
        return getattr(agent, "color_code", None) if agent else None

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url
        
class MarketCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    owner_first_name = serializers.CharField(source="owner.first_name", required=False, allow_blank=True)
    owner_last_name = serializers.CharField(source="owner.last_name", required=False, allow_blank=True)
    owner_phone_number = serializers.CharField(source="owner.phone_number", required=False, allow_blank=True)

    class Meta:
        model = Market
        fields = [
            "id",
            "owner_first_name",
            "owner_last_name",
            "owner_phone_number",
            "name",
            "description",
            "image",
            "discount_percentage",
            "created_by",
            "latitude",
            "longitude",
        ]
        extra_kwargs = {"created_by": {"read_only": True}, "id": {"read_only": True}}

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            user
            and getattr(user, "role_type", None) == "CUSTOMER"
            and self.instance is None
            and user.markets.exists()
        ):
            raise serializers.ValidationError(
                {"detail": "Siz allaqachon o'z do'koningizni qo'shgansiz"}
            )
        return attrs

    def _apply_owner(self, owner_data, user):
        if user and user.role_type == "CUSTOMER":
            return user
        if owner_data and owner_data.get("phone_number"):
            owner = User.objects.filter(phone_number=owner_data["phone_number"]).first()
            if owner is None:
                owner = User.objects.create_user(
                    phone_number=owner_data["phone_number"],
                    password=None,
                    first_name=owner_data.get("first_name", ""),
                    last_name=owner_data.get("last_name", ""),
                    role_type="CUSTOMER",
                )
            return owner
        return None

    def create(self, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        if latitude is not None and longitude is not None:
            validated_data["location"] = Point(longitude, latitude, srid=4326)

        owner_data = validated_data.pop("owner", None)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        owner = self._apply_owner(owner_data, user)
        if owner:
            validated_data["owner"] = owner
        if user and user.is_authenticated:
            validated_data["created_by"] = user
        return Market.objects.create(**validated_data)

    def update(self, instance, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        owner_data = validated_data.pop("owner", None)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if latitude is not None and longitude is not None:
            instance.location = Point(longitude, latitude, srid=4326)
        if user and user.role_type != "CUSTOMER":
            owner = self._apply_owner(owner_data, user)
            if owner:
                instance.owner = owner
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def validate_owner_phone_number(self, value):
        if not value:
            return value
        regex = r"^\+998\d{9}$"
        if not re.compile(regex).match(value):
            raise serializers.ValidationError(
                "Telefon raqami noto'g'ri formatda. Iltimos, +998XXXXXXXXX formatida kiriting."
            )
        return value

class MarketReadSerializer(MarketCreateSerializer):
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    status = serializers.CharField(source='statuses.get_status_display', read_only=True)
    status_color_code = serializers.CharField(source='statuses.get_color_code_display', read_only=True)
    created_by = UserBaseReadSerializer(read_only=True)
    last_order_taken_by = UserBaseReadSerializer(source='statuses.last_order.ordered_by', read_only=True)
    last_order_given_by = UserBaseReadSerializer(source='statuses.last_order.delivered_by', read_only=True)
    status_code = serializers.CharField(source='statuses.status', read_only=True)
    credit_amount = serializers.DecimalField(max_digits=20, decimal_places=3, read_only=True)
    last_order_id = serializers.SerializerMethodField()
    class Meta(MarketCreateSerializer.Meta):
        fields = ['id','status','status_code', 'status_color_code','created_at','last_order_taken_by','last_order_given_by','credit_amount','last_order_id'] + MarketCreateSerializer.Meta.fields

    def get_last_order_id(self, obj):
        statuses = getattr(obj, "statuses", None)
        return getattr(statuses, "last_order_id", None) if statuses else None 
        
    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None