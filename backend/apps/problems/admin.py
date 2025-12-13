from django.contrib import admin

from .models import Answer, Problem, ProblemGroup


class ProblemInline(admin.TabularInline):
    """ProblemGroup詳細画面でProblemを表示するInline."""

    model = Problem
    extra = 0
    fields = ["order_index", "problem_type", "problem_body", "created_at"]
    readonly_fields = ["created_at"]
    ordering = ["order_index"]


@admin.register(ProblemGroup)
class ProblemGroupAdmin(admin.ModelAdmin):
    """ProblemGroup用のAdmin設定."""

    list_display = [
        "id",
        "title",
        "difficulty",
        "app_scale",
        "mode",
        "created_by_user",
        "created_at",
    ]
    list_filter = ["difficulty", "app_scale", "mode", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    inlines = [ProblemInline]

    fieldsets = (
        (None, {"fields": ("title", "description")}),
        (
            "設定",
            {"fields": ("difficulty", "app_scale", "mode", "created_by_user")},
        ),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    """Problem用のAdmin設定."""

    list_display = [
        "id",
        "problem_group",
        "problem_type",
        "order_index",
        "created_at",
    ]
    list_filter = ["problem_type", "created_at"]
    search_fields = ["problem_body"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["problem_group", "order_index"]

    fieldsets = (
        (None, {"fields": ("problem_group", "problem_type", "order_index")}),
        ("問題内容", {"fields": ("problem_body",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """Answer用のAdmin設定."""

    list_display = [
        "answer_id",
        "user",
        "problem",
        "grade",
        "created_at",
    ]
    list_filter = ["grade", "created_at"]
    search_fields = ["answer_body"]
    readonly_fields = ["grade", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("problem", "user")}),
        ("回答内容", {"fields": ("answer_body",)}),
        ("採点結果", {"fields": ("grade",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )
