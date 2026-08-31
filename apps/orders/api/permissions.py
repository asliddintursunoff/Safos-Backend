from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class CanUserUpdateDeleteOrder(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role_type", None)
        if role == "ADMIN":
            return True
        if role == "DELIVERER":
            if request.method == "DELETE":
                return obj.ordered_by_id == user.id
            return True
        if role == "CUSTOMER":
            owner_id = getattr(obj.market, "owner_id", None)
            if obj.ordered_by_id != user.id and owner_id != user.id:
                return False
            if request.method in SAFE_METHODS:
                return True
            if request.method == "DELETE":
                return obj.status == "PENDING"
            return obj.status in ("PENDING", "APPROVED")
        if role == "AGENT":
            if request.method in SAFE_METHODS:
                return True
            if request.method == "DELETE":
                return obj.ordered_by_id == user.id and obj.status == "PENDING"
            return obj.status in ("PENDING", "APPROVED")
        return False


class CanCreateOrder(permissions.BasePermission):
    message = "Buyurtma yaratishga ruxsat yo'q"

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method != "POST":
            return True
        return request.user.role_type in ("ADMIN", "AGENT", "CUSTOMER", "DELIVERER")


class IsADMIN(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role_type == "ADMIN"
        )


class IsAdminOrDeliverer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role_type in ("ADMIN", "DELIVERER")
        )