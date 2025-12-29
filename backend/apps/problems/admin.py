from django.contrib import admin

from .models import (
    Answer,
    Explanation,
    FavoriteProblemGroup,
    ModelAnswer,
    Problem,
    ProblemGroup,
    ProblemGroupAttempt,
    ProblemGroupEvaluation,
)


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
        "problem_group_id",
        "title",
        "difficulty",
        "created_at",
    ]
    list_filter = ["difficulty", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    inlines = [ProblemInline]

    fieldsets = (
        (None, {"fields": ("title", "description")}),
        (
            "設定",
            {"fields": ("difficulty",)},
        ),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    """Problem用のAdmin設定."""

    list_display = [
        "problem_id",
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
        "version",
        "grade",
        "created_at",
    ]
    list_filter = ["grade", "version", "created_at"]
    search_fields = ["answer_body"]
    readonly_fields = ["grade", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("problem", "user", "version")}),
        ("回答内容", {"fields": ("answer_body",)}),
        ("採点結果", {"fields": ("grade",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ModelAnswer)
class ModelAnswerAdmin(admin.ModelAdmin):
    """ModelAnswer用のAdmin設定."""

    list_display = [
        "model_answer_id",
        "problem",
        "version",
        "created_at",
    ]
    list_filter = ["version", "created_at"]
    search_fields = ["model_answer"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["problem", "version"]

    fieldsets = (
        (None, {"fields": ("problem", "version")}),
        ("模範解答", {"fields": ("model_answer",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    """Explanation用のAdmin設定."""

    list_display = [
        "explanation_id",
        "answer",
        "version",
        "created_at",
    ]
    list_filter = ["version", "created_at"]
    search_fields = ["explanation_body"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["answer", "version"]

    fieldsets = (
        (None, {"fields": ("answer", "version")}),
        ("解説", {"fields": ("explanation_body",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProblemGroupEvaluation)
class ProblemGroupEvaluationAdmin(admin.ModelAdmin):
    """ProblemGroupEvaluation用のAdmin設定."""

    list_display = [
        "evaluation_id",
        "user",
        "problem_group",
        "evaluation",
        "created_at",
    ]
    list_filter = ["evaluation", "created_at"]
    search_fields = ["evaluation_reason"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("user", "problem_group", "evaluation")}),
        ("理由", {"fields": ("evaluation_reason",)}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(FavoriteProblemGroup)
class FavoriteProblemGroupAdmin(admin.ModelAdmin):
    """FavoriteProblemGroup用のAdmin設定."""

    list_display = [
        "favorite_id",
        "user",
        "problem_group",
        "created_at",
    ]
    list_filter = ["created_at"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("user", "problem_group")}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProblemGroupAttempt)
class ProblemGroupAttemptAdmin(admin.ModelAdmin):
    """ProblemGroupAttempt用のAdmin設定."""

    list_display = [
        "attempt_id",
        "user",
        "problem_group",
        "created_at",
    ]
    list_filter = ["created_at"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("user", "problem_group")}),
        ("日時", {"fields": ("created_at", "updated_at")}),
    )
