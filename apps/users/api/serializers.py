from rest_framework import serializers

from apps.common.choices import USER_ROLE_CHOICES
from apps.users.api.auth import normalize_phone
from apps.users.models import User

WORKER_ROLES = ("ADMIN", "DELIVERER", "AGENT")


class UserBaseReadSerializer(serializers.ModelSerializer):
    role_type = serializers.CharField(source="get_role_type_display")

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "phone_number", "role_type", "photo"]


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=4)
    markets_count = serializers.IntegerField(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "role_type",
            "color_code",
            "is_active",
            "telegram_id",
            "password",
            "markets_count",
            "photo",
        ]
        extra_kwargs = {
            "telegram_id": {"read_only": True},
        }

    def validate_phone_number(self, value):
        return normalize_phone(value)

    def validate_role_type(self, value):
        if value not in USER_ROLE_CHOICES:
            raise serializers.ValidationError("Noto'g'ri rol")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        instance = self.instance
        role = attrs.get("role_type", getattr(instance, "role_type", None))
        password = attrs.get("password")

        if instance is None and role in WORKER_ROLES and not password:
            raise serializers.ValidationError(
                {"password": "Ishchilar uchun parol majburiy"}
            )

        if (
            request
            and instance
            and instance.pk == getattr(request.user, "pk", None)
        ):
            if "role_type" in attrs and attrs["role_type"] != instance.role_type:
                raise serializers.ValidationError(
                    {"role_type": "O'z rolingizni o'zgartira olmaysiz"}
                )
            if "is_active" in attrs and attrs["is_active"] is False:
                raise serializers.ValidationError(
                    {"is_active": "O'z akkauntingizni o'chira olmaysiz"}
                )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        # keep existing behavior for admin updates
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer used when a user updates their own profile."""

    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "photo", "password"]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def update(self, instance, validated_data):
        photo = validated_data.pop("photo", serializers.empty)
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if photo is not serializers.empty:
            setattr(instance, "photo", photo)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
