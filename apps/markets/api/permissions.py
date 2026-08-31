from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Faqat admin uchun ruxsat berilgan"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role_type", None) == "ADMIN"
        )
