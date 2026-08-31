import re

from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.permissions import WORKER_ROLES
from apps.users.models import User


PHONE_RE = re.compile(r"^\+998\d{9}$")


def normalize_phone(value):
    if not value:
        raise ValidationError({"phone_number": "Telefon raqam kiritilishi shart"})
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("998") and len(digits) == 12:
        phone = f"+{digits}"
    elif len(digits) == 9:
        phone = f"+998{digits}"
    else:
        phone = str(value).strip()
    if not PHONE_RE.match(phone):
        raise ValidationError(
            {"phone_number": "Telefon +998XXXXXXXXX formatida bo'lishi kerak"}
        )
    return phone


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role_type"] = user.role_type
    refresh["first_name"] = user.first_name
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def user_payload(user):
    markets = []
    if user.role_type == "CUSTOMER":
        markets = [
            {"id": str(m.id), "name": m.name}
            for m in user.markets.all().only("id", "name")
        ]
    return {
        "id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "role_type": user.role_type,
        "role_label": user.get_role_type_display(),
        "color_code": user.color_code,
        "is_active": user.is_active,
        "telegram_id": user.telegram_id,
        "photo": user.photo.url if getattr(user, "photo", None) else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "markets": markets,
    }


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(required=False, allow_blank=True)
    telegram_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_phone_number(self, value):
        return normalize_phone(value)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]
        password = serializer.validated_data.get("password") or ""
        telegram_id = serializer.validated_data.get("telegram_id")

        user = User.objects.filter(phone_number=phone, is_active=True).first()
        if user is None:
            return Response(
                {"detail": "Bu telefon raqam tizimda yo'q"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.role_type in WORKER_ROLES:
            if not password:
                return Response(
                    {"detail": "Ishchilar parol kiritishi shart"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not user.has_usable_password() or not user.check_password(password):
                return Response(
                    {"detail": "Telefon yoki parol noto'g'ri"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif user.role_type == "CUSTOMER":
            if password and user.has_usable_password() and not user.check_password(password):
                return Response(
                    {"detail": "Telefon yoki parol noto'g'ri"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        else:
            return Response(
                {"detail": "Noma'lum foydalanuvchi turi"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        fields = ["last_login"]
        user.last_login = timezone.now()
        if telegram_id and user.telegram_id is None:
            if not User.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).exists():
                user.telegram_id = telegram_id
                fields.append("telegram_id")
        user.save(update_fields=fields)

        data = tokens_for_user(user)
        data["user"] = user_payload(user)
        return Response(data)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        raw = request.data.get("refresh")
        if not raw:
            raise ValidationError({"refresh": "refresh token kerak"})
        try:
            token = RefreshToken(raw)
            token.blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Token yaroqsiz"})
        return Response({"detail": "Chiqildi"})


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = (
            User.objects.prefetch_related("markets")
            .get(pk=request.user.pk)
        )
        return Response(user_payload(user))


class AllowAnyTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
