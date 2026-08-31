from rest_framework.permissions import BasePermission, SAFE_METHODS

WORKER_ROLES = ("ADMIN", "DELIVERER", "AGENT")


class IsAdminRole(BasePermission):
    message = "Faqat admin uchun ruxsat berilgan"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role_type", None) == "ADMIN"
        )


class IsAdminOrDeliverer(BasePermission):
    message = "Faqat admin yoki yetkazuvchi uchun ruxsat berilgan"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role_type", None) in ("ADMIN", "DELIVERER")
        )


class IsAuthenticatedAgentOrAbove(BasePermission):
    message = "Kirish uchun tizimga kiring"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role_type == "ADMIN"


class IsAdminOrOwner(BasePermission):
    message = "Faqat admin yoki ob'ekt egasi ruxsatga ega"

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "role_type", None) == "ADMIN":
            return True
        # For User objects, allow owner
        try:
            return getattr(obj, "id", None) == getattr(user, "id", None)
        except Exception:
            return False


class CanCreateMarket(BasePermission):
    message = "Do'kon qo'shishga ruxsat yo'q"

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "POST":
            return user.role_type in ("ADMIN", "AGENT", "DELIVERER", "CUSTOMER")
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(user, "role_type", None)
        if role == "ADMIN":
            return True
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return role == "ADMIN"
        if role == "CUSTOMER":
            return obj.owner_id == user.id
        if role in ("AGENT", "DELIVERER"):
            return obj.created_by_id == user.id or obj.owner_id == user.id
        return False


class IsAdminOrDelivererOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role_type in ("ADMIN", "DELIVERER")
