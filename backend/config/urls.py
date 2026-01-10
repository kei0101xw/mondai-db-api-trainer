"""URL configuration for config project."""

from django.contrib import admin
from django.urls import include, path

from apps.problems.views import (
    RankingView,
    DashboardView,
    GradeAnswerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.auth.api.urls")),
    path("api/v1/problem-groups/", include("apps.problems.urls")),
    path("api/v1/grade", GradeAnswerView.as_view(), name="grade"),
    path("api/v1/rankings", RankingView.as_view(), name="rankings"),
    path("api/v1/dashboard", DashboardView.as_view(), name="dashboard"),
]
