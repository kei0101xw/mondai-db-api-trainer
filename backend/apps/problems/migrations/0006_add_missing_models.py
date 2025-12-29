# Generated manually on 2025-12-29
# Add missing models and fields to align DB schema with current models.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("problems", "0005_remove_unused_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # answers: add version field (default 1)
        migrations.AddField(
            model_name="answer",
            name="version",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="回答バージョン",
                help_text="回答の世代を示すバージョン番号",
            ),
        ),
        # model_answers table
        migrations.CreateModel(
            name="ModelAnswer",
            fields=[
                (
                    "model_answer_id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="模範解答ID",
                    ),
                ),
                ("version", models.PositiveIntegerField(verbose_name="バージョン")),
                (
                    "model_answer",
                    models.TextField(verbose_name="模範解答"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "problem",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="model_answers",
                        to="problems.problem",
                        verbose_name="問題",
                    ),
                ),
            ],
            options={
                "verbose_name": "模範解答",
                "verbose_name_plural": "模範解答",
                "db_table": "model_answers",
                "ordering": ["problem", "version"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["problem", "version"],
                        name="model_answers_problem_version_unique",
                    )
                ],
            },
        ),
        # explanations table
        migrations.CreateModel(
            name="Explanation",
            fields=[
                (
                    "explanation_id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="解説ID",
                    ),
                ),
                ("version", models.PositiveIntegerField(verbose_name="バージョン")),
                (
                    "explanation_body",
                    models.TextField(verbose_name="解説本文"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "answer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="explanations",
                        to="problems.answer",
                        verbose_name="回答",
                    ),
                ),
            ],
            options={
                "verbose_name": "解説",
                "verbose_name_plural": "解説",
                "db_table": "explanations",
                "ordering": ["answer", "version"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["answer", "version"],
                        name="explanations_answer_version_unique",
                    )
                ],
            },
        ),
        # problem_group_attempts table
        migrations.CreateModel(
            name="ProblemGroupAttempt",
            fields=[
                (
                    "attempt_id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="挑戦ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "problem_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="problems.problemgroup",
                        verbose_name="問題グループ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="problem_group_attempts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="ユーザー",
                    ),
                ),
            ],
            options={
                "verbose_name": "問題グループ挑戦",
                "verbose_name_plural": "問題グループ挑戦",
                "db_table": "problem_group_attempts",
                "constraints": [
                    models.UniqueConstraint(
                        fields=["problem_group", "user"],
                        name="problem_group_attempt_unique",
                    )
                ],
            },
        ),
        # problems_groups_evaluation table
        migrations.CreateModel(
            name="ProblemGroupEvaluation",
            fields=[
                (
                    "evaluation_id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="評価ID",
                    ),
                ),
                (
                    "evaluation",
                    models.CharField(
                        max_length=10,
                        choices=[("low", "低評価"), ("high", "高評価")],
                        verbose_name="評価",
                    ),
                ),
                (
                    "evaluation_reason",
                    models.TextField(
                        null=True,
                        blank=True,
                        verbose_name="評価理由",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "problem_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluations",
                        to="problems.problemgroup",
                        verbose_name="問題グループ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="problem_group_evaluations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="ユーザー",
                    ),
                ),
            ],
            options={
                "verbose_name": "問題グループ評価",
                "verbose_name_plural": "問題グループ評価",
                "db_table": "problems_groups_evaluation",
                "constraints": [
                    models.UniqueConstraint(
                        fields=["user", "problem_group"],
                        name="problem_group_evaluation_unique",
                    ),
                    models.CheckConstraint(
                        check=models.Q(evaluation__in=["low", "high"]),
                        name="problem_group_evaluation_valid",
                    ),
                ],
            },
        ),
        # favorite_problems_groups table
        migrations.CreateModel(
            name="FavoriteProblemGroup",
            fields=[
                (
                    "favorite_id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="お気に入りID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "problem_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorited_by",
                        to="problems.problemgroup",
                        verbose_name="問題グループ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorite_problem_groups",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="ユーザー",
                    ),
                ),
            ],
            options={
                "verbose_name": "問題グループお気に入り",
                "verbose_name_plural": "問題グループお気に入り",
                "db_table": "favorite_problems_groups",
                "constraints": [
                    models.UniqueConstraint(
                        fields=["user", "problem_group"],
                        name="favorite_problem_group_unique",
                    )
                ],
            },
        ),
    ]
