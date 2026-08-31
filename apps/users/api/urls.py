from django.urls import path

from apps.users.api.auth import AllowAnyTokenRefreshView, LoginAPIView, LogoutAPIView, MeAPIView
from apps.users.api.views import UserDetailView, UserListView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="user-login"),
    path("logout/", LogoutAPIView.as_view(), name="user-logout"),
    path("refresh/", AllowAnyTokenRefreshView.as_view(), name="user-token-refresh"),
    path("me/", MeAPIView.as_view(), name="user-me"),
    path("", UserListView.as_view(), name="user-list"),
    path("<uuid:id>/", UserDetailView.as_view(), name="user-detail"),
]
