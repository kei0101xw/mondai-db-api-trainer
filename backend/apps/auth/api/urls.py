"""認証APIのURLルーティング."""

from django.urls import path

from .views import get_csrf_token

urlpatterns = [
    path("csrf", get_csrf_token, name="csrf-token"),
]
