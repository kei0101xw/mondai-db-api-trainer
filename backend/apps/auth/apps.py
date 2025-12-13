"""Django App設定."""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    """認証アプリのApp設定."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth"
    label = "accounts"  # django.contrib.authとの競合を避けるため
    verbose_name = "認証・アカウント"
