"""Django Admin設定."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom Userモデル用のAdmin設定."""

    list_display = ["user_id", "email", "name", "is_active", "is_staff", "created_at"]
    list_filter = ["is_active", "is_staff", "created_at"]
    search_fields = ["email", "name"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("個人情報", {"fields": ("name", "icon_url")}),
        (
            "権限",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("重要な日付", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]
