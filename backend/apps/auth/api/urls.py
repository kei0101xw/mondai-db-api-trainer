"""認証APIのURLルーティング."""

from django.urls import path

from .views import (
    get_csrf_token,
    get_current_user_view,
    login_user_view,
    logout_user_view,
    register_user_view,
)

urlpatterns = [
    path("csrf", get_csrf_token, name="csrf-token"),
    path("register", register_user_view, name="register"),
    path("login", login_user_view, name="login"),
    path("logout", logout_user_view, name="logout"),
    path("me", get_current_user_view, name="current-user"),
]
