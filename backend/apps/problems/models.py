from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ProblemGroup(models.Model):
    """
    問題の題材（例：SNSアプリ、ECサイトなど）
    """

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class AppScale(models.TextChoices):
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        LARGE = "large", "Large"

    class Mode(models.TextChoices):
        DB_ONLY = "db_only", "DB Only"
        API_ONLY = "api_only", "API Only"
        BOTH = "both", "Both"

    problem_group_id = models.BigAutoField(
        primary_key=True, verbose_name="問題グループID"
    )
    title = models.CharField(max_length=255, verbose_name="タイトル")
    description = models.TextField(verbose_name="説明")
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        verbose_name="難易度",
    )
    app_scale = models.CharField(
        max_length=10,
        choices=AppScale.choices,
        verbose_name="アプリ規模",
    )
    mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        verbose_name="モード",
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="problem_groups",
        verbose_name="作成者",
        null=True,  # ゲストユーザーの場合はNULL
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "problem_groups"
        verbose_name = "問題グループ"
        verbose_name_plural = "問題グループ"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.difficulty})"


class Problem(models.Model):
    """
    題材内の小問（DB設計問題 or API設計問題）
    """

    class ProblemType(models.TextChoices):
        DB = "db", "DB Design"
        API = "api", "API Design"

    problem_id = models.BigAutoField(primary_key=True, verbose_name="問題ID")
    problem_group = models.ForeignKey(
        ProblemGroup,
        on_delete=models.CASCADE,
        related_name="problems",
        verbose_name="問題グループ",
    )
    problem_type = models.CharField(
        max_length=10,
        choices=ProblemType.choices,
        verbose_name="問題タイプ",
    )
    order_index = models.PositiveIntegerField(verbose_name="問題順序")
    problem_body = models.TextField(verbose_name="問題本文")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "problems"
        verbose_name = "問題"
        verbose_name_plural = "問題"
        ordering = ["problem_group", "order_index"]
        unique_together = [["problem_group", "order_index"]]

    def __str__(self) -> str:
        return f"{self.problem_group.title} - {self.order_index} ({self.problem_type})"


class Answer(models.Model):
    """
    小問に対する回答
    """

    class Grade(models.IntegerChoices):
        INCORRECT = 0, "×"
        PARTIAL = 1, "△"
        CORRECT = 2, "○"

    answer_id = models.BigAutoField(primary_key=True, verbose_name="回答ID")
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="問題",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="ユーザー",
    )
    answer_body = models.TextField(verbose_name="回答本文")
    grade = models.IntegerField(
        choices=Grade.choices,
        verbose_name="採点結果",
        help_text="0:×, 1:△, 2:○",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "answers"
        verbose_name = "回答"
        verbose_name_plural = "回答"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        grade_display = self.get_grade_display()
        return f"{self.user.name} - {self.problem} ({grade_display})"
