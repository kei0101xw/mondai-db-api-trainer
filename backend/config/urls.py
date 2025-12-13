"""URL configuration for config project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.auth.api.urls")),
    path("api/v1/problem-groups/", include("apps.problems.urls")),
]
