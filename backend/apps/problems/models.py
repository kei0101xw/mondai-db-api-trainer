from django.db import models
from django.db.models import Q
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "problem_groups"
        verbose_name = "問題グループ"
        verbose_name_plural = "問題グループ"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(difficulty__in=["easy", "medium", "hard"]),
                name="problem_groups_difficulty_valid",
            ),
        ]

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
        constraints = [
            models.UniqueConstraint(
                fields=["problem_group", "order_index"],
                name="problems_group_order_unique",
            ),
            models.CheckConstraint(
                check=Q(problem_type__in=["db", "api"]),
                name="problems_problem_type_valid",
            ),
        ]

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
    version = models.PositiveIntegerField(
        default=1,
        verbose_name="回答バージョン",
        help_text="回答の世代を示すバージョン番号",
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
        constraints = [
            models.CheckConstraint(
                check=Q(grade__in=[0, 1, 2]),
                name="answers_grade_valid",
            ),
        ]

    def __str__(self) -> str:
        grade_display = self.get_grade_display()
        return f"{self.user.name} - {self.problem} ({grade_display})"


class ModelAnswer(models.Model):
    """
    小問に対する模範解答（複数バージョンを保持）。
    """

    model_answer_id = models.BigAutoField(primary_key=True, verbose_name="模範解答ID")
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="model_answers",
        verbose_name="問題",
    )
    version = models.PositiveIntegerField(verbose_name="バージョン")
    model_answer = models.TextField(verbose_name="模範解答")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "model_answers"
        verbose_name = "模範解答"
        verbose_name_plural = "模範解答"
        ordering = ["problem", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["problem", "version"],
                name="model_answers_problem_version_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.problem} v{self.version}"


class Explanation(models.Model):
    """
    回答に紐づく解説（採点結果と同じバージョンで保持）。
    """

    explanation_id = models.BigAutoField(primary_key=True, verbose_name="解説ID")
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="explanations",
        verbose_name="回答",
    )
    version = models.PositiveIntegerField(verbose_name="バージョン")
    explanation_body = models.TextField(verbose_name="解説本文")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "explanations"
        verbose_name = "解説"
        verbose_name_plural = "解説"
        ordering = ["answer", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "version"],
                name="explanations_answer_version_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.answer} v{self.version}"


class ProblemGroupEvaluation(models.Model):
    """
    題材への評価（高評価・低評価）。
    """

    class Evaluation(models.TextChoices):
        LOW = "low", "低評価"
        HIGH = "high", "高評価"

    evaluation_id = models.BigAutoField(primary_key=True, verbose_name="評価ID")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="problem_group_evaluations",
        verbose_name="ユーザー",
    )
    problem_group = models.ForeignKey(
        ProblemGroup,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="問題グループ",
    )
    evaluation = models.CharField(
        max_length=10,
        choices=Evaluation.choices,
        verbose_name="評価",
    )
    evaluation_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="評価理由",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "problems_groups_evaluation"
        verbose_name = "問題グループ評価"
        verbose_name_plural = "問題グループ評価"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "problem_group"],
                name="problem_group_evaluation_unique",
            ),
            models.CheckConstraint(
                check=Q(evaluation__in=["low", "high"]),
                name="problem_group_evaluation_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.problem_group} - {self.get_evaluation_display()}"


class FavoriteProblemGroup(models.Model):
    """
    題材のお気に入り。
    """

    favorite_id = models.BigAutoField(primary_key=True, verbose_name="お気に入りID")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_problem_groups",
        verbose_name="ユーザー",
    )
    problem_group = models.ForeignKey(
        ProblemGroup,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="問題グループ",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "favorite_problems_groups"
        verbose_name = "問題グループお気に入り"
        verbose_name_plural = "問題グループお気に入り"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "problem_group"],
                name="favorite_problem_group_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.name} -> {self.problem_group}"


class ProblemGroupAttempt(models.Model):
    """
    ログインユーザーが題材を解き終えたことを記録。
    """

    attempt_id = models.BigAutoField(primary_key=True, verbose_name="挑戦ID")
    problem_group = models.ForeignKey(
        ProblemGroup,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="問題グループ",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="problem_group_attempts",
        verbose_name="ユーザー",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "problem_group_attempts"
        verbose_name = "問題グループ挑戦"
        verbose_name_plural = "問題グループ挑戦"
        constraints = [
            models.UniqueConstraint(
                fields=["problem_group", "user"],
                name="problem_group_attempt_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.name} -> {self.problem_group}"
