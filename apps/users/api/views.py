from django.db.models import Count
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.permissions import IsAdminRole, IsAdminOrOwner
from apps.users.models import User
from .serializers import UserSerializer, UserUpdateSerializer


class UserListView(ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["role_type", "is_active"]
    search_fields = ["first_name", "last_name", "phone_number"]

    def get_queryset(self):
        return User.objects.annotate(markets_count=Count("markets")).order_by(
            "role_type", "first_name"
        )


class UserDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrOwner]
    lookup_field = "id"

    def get_queryset(self):
        return User.objects.annotate(markets_count=Count("markets"))

    def get_serializer_class(self):
        # Use a lightweight serializer when users update their own profile
        if self.request.method in ("PUT", "PATCH") and self.request.user and str(self.request.user.id) == str(self.kwargs.get("id")):
            return UserUpdateSerializer
        return super().get_serializer_class()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError("O'z akkauntingizni o'chira olmaysiz")
        instance.delete()
