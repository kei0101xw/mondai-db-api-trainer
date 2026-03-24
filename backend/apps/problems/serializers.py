from rest_framework import serializers

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_PERIODS = {"daily", "weekly", "monthly", "all"}
VALID_SCORE_TYPES = {"problem_count", "correct_count", "grade_sum"}
MAX_ANSWER_BODY_LENGTH = 50000
MAX_REQUIREMENT_QUESTION_LENGTH = 5000


class GenerateProblemRequestSerializer(serializers.Serializer):
    """問題生成 API の入力."""

    min_stock = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        error_messages={
            "invalid": "min_stock は1以上の整数を指定してください",
            "min_value": "min_stock は1以上の整数を指定してください",
        },
    )
    difficulties = serializers.ListField(
        required=False,
        error_messages={
            "not_a_list": "difficulties は配列で指定してください",
        },
    )
    difficulty = serializers.CharField(required=False)

    def validate_difficulties(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("difficulties は配列で指定してください")
        if not all(
            isinstance(item, str) and item in VALID_DIFFICULTIES for item in value
        ):
            raise serializers.ValidationError(
                "difficulties の要素は easy, medium, hard のいずれかを指定してください"
            )
        return value

    def validate_difficulty(self, value):
        if value not in VALID_DIFFICULTIES:
            raise serializers.ValidationError(
                "difficulty は easy, medium, hard のいずれかを指定してください"
            )
        return value


class ProblemGroupQuerySerializer(serializers.Serializer):
    """問題取得 API のクエリ."""

    difficulty = serializers.CharField(
        required=True,
        error_messages={
            "required": "difficulty は easy, medium, hard のいずれかを指定してください",
            "blank": "difficulty は easy, medium, hard のいずれかを指定してください",
        },
    )

    def validate_difficulty(self, value):
        if value not in VALID_DIFFICULTIES:
            raise serializers.ValidationError(
                "difficulty は easy, medium, hard のいずれかを指定してください"
            )
        return value


class GradeAnswerRequestSerializer(serializers.Serializer):
    """採点 API の入力."""

    problem_group_id = serializers.IntegerField(required=False)
    guest_token = serializers.CharField(required=False, allow_blank=True)
    answers = serializers.ListField(
        required=True,
        allow_empty=False,
        child=serializers.DictField(),
        error_messages={
            "required": "answers は1件以上の配列である必要があります",
            "empty": "answers は1件以上の配列である必要があります",
            "not_a_list": "answers は1件以上の配列である必要があります",
        },
    )

    def validate(self, attrs):
        request = self.context["request"]
        is_authenticated = request.user.is_authenticated
        has_problem_group_id = attrs.get("problem_group_id") is not None
        has_guest_token = attrs.get("guest_token") is not None

        if is_authenticated:
            if not has_problem_group_id:
                raise serializers.ValidationError(
                    "ログインユーザーは problem_group_id が必須です"
                )
            if has_guest_token:
                raise serializers.ValidationError(
                    "ログインユーザーは guest_token を指定できません"
                )
        else:
            if has_problem_group_id:
                raise serializers.ValidationError(
                    "ゲストユーザーは problem_group_id を指定できません"
                )
            if not has_guest_token:
                raise serializers.ValidationError(
                    "ゲストユーザーは guest_token が必須です"
                )

        seen_problem_ids = set()
        normalized_answers = []

        for idx, answer in enumerate(attrs["answers"]):
            answer_body = answer.get("answer_body")
            if (
                not isinstance(answer_body, str)
                or not answer_body
                or not answer_body.strip()
            ):
                raise serializers.ValidationError(
                    f"answers[{idx}]: answer_body は必須です"
                )

            if len(answer_body) > MAX_ANSWER_BODY_LENGTH:
                raise serializers.ValidationError(
                    f"answers[{idx}]: 回答は{MAX_ANSWER_BODY_LENGTH}文字以下である必要があります"
                )

            problem_id = answer.get("problem_id")
            if problem_id is None:
                raise serializers.ValidationError(
                    f"answers[{idx}]: problem_id は必須です"
                )

            if problem_id in seen_problem_ids:
                raise serializers.ValidationError(
                    f"answers[{idx}]: problem_id が重複しています"
                )

            seen_problem_ids.add(problem_id)
            normalized_answers.append(
                {
                    "problem_id": problem_id,
                    "answer_body": answer_body,
                }
            )

        attrs["answers"] = normalized_answers
        return attrs


class CompleteProblemGroupRequestSerializer(serializers.Serializer):
    """題材完了 API の入力."""

    guest_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        if not request.user.is_authenticated and not attrs.get("guest_token"):
            raise serializers.ValidationError("guest_token は必須です")
        return attrs


class RequirementQuestionRequestSerializer(serializers.Serializer):
    """要件問い合わせ API の入力."""

    question = serializers.CharField(
        required=True,
        max_length=MAX_REQUIREMENT_QUESTION_LENGTH,
        trim_whitespace=True,
        error_messages={
            "required": "question は必須です",
            "blank": "question は必須です",
            "max_length": f"question は {MAX_REQUIREMENT_QUESTION_LENGTH} 文字以下で入力してください",
        },
    )


class RequirementTurnSerializer(serializers.Serializer):
    """要件問い合わせの1ターン."""

    id = serializers.IntegerField()
    turn_no = serializers.IntegerField()
    user_question = serializers.CharField()
    ai_answer = serializers.CharField()


class RequirementItemSerializer(serializers.Serializer):
    """構造化された追加要件."""

    id = serializers.IntegerField()
    subject = serializers.CharField()
    predicate = serializers.CharField()
    object_value = serializers.CharField()
    detail_text = serializers.CharField()


class RequirementQuestionDataSerializer(serializers.Serializer):
    """要件問い合わせレスポンスの data 部分."""

    turn = RequirementTurnSerializer()
    requirement_items = RequirementItemSerializer(many=True)


class RequirementListDataSerializer(serializers.Serializer):
    """要件一覧レスポンスの data 部分."""

    turn_logs = RequirementTurnSerializer(many=True)
    requirement_items = RequirementItemSerializer(many=True)


class MyProblemGroupsQuerySerializer(serializers.Serializer):
    """復習一覧 API のクエリ."""

    difficulty = serializers.CharField(required=False)

    def validate_difficulty(self, value):
        if value not in VALID_DIFFICULTIES:
            raise serializers.ValidationError(
                "difficulty は easy, medium, hard のいずれかを指定してください"
            )
        return value


class RankingQuerySerializer(serializers.Serializer):
    """ランキング API のクエリ."""

    period = serializers.CharField(required=False, default="daily")
    score_type = serializers.CharField(required=False, default="problem_count")
    limit = serializers.IntegerField(required=False, default=5)

    def validate_period(self, value):
        if value not in VALID_PERIODS:
            raise serializers.ValidationError(
                f"period は {', '.join(VALID_PERIODS)} のいずれかを指定してください"
            )
        return value

    def validate_score_type(self, value):
        if value not in VALID_SCORE_TYPES:
            raise serializers.ValidationError(
                f"score_type は {', '.join(VALID_SCORE_TYPES)} のいずれかを指定してください"
            )
        return value

    def validate_limit(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError(
                "limit は 1 から 100 の整数を指定してください"
            )
        return value


class ProblemGroupSummarySerializer(serializers.Serializer):
    """題材の基本情報."""

    problem_group_id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    difficulty = serializers.CharField()


class ProblemGroupDetailSerializer(ProblemGroupSummarySerializer):
    """題材詳細情報."""

    created_at = serializers.CharField()
    completed_at = serializers.CharField(allow_null=True)


class ProblemSerializer(serializers.Serializer):
    """小問情報."""

    problem_id = serializers.IntegerField()
    order_index = serializers.IntegerField()
    problem_type = serializers.CharField()
    problem_body = serializers.CharField()


class ProblemWithGroupSerializer(ProblemSerializer):
    """problem_group_id を含む小問情報."""

    problem_group_id = serializers.IntegerField()


class ProblemGroupFetchDataSerializer(serializers.Serializer):
    """新規問題取得レスポンスの data 部分."""

    kind = serializers.CharField()
    guest_token = serializers.CharField(required=False)
    problem_group = ProblemGroupSummarySerializer()
    problems = ProblemWithGroupSerializer(many=True)


class ProblemRefSerializer(serializers.Serializer):
    """採点結果に含まれる問題参照情報."""

    problem_id = serializers.IntegerField()
    order_index = serializers.IntegerField()


class ExplanationSerializer(serializers.Serializer):
    """解説情報."""

    version = serializers.IntegerField()
    explanation_body = serializers.CharField()


class ModelAnswerSerializer(serializers.Serializer):
    """模範解答情報."""

    version = serializers.IntegerField()
    model_answer = serializers.CharField()


class GradeResultSerializer(serializers.Serializer):
    """採点結果."""

    problem_ref = ProblemRefSerializer()
    problem_type = serializers.CharField()
    grade = serializers.IntegerField()
    grade_display = serializers.CharField()
    explanation = ExplanationSerializer()
    model_answer = ModelAnswerSerializer(allow_null=True)
    answer_id = serializers.IntegerField(required=False)


class GradeResponseDataSerializer(serializers.Serializer):
    """採点レスポンスの data 部分."""

    results = GradeResultSerializer(many=True)


class CompleteProblemGroupDataSerializer(serializers.Serializer):
    """題材完了レスポンスの data 部分."""

    ok = serializers.BooleanField()


class AnswerSummarySerializer(serializers.Serializer):
    """題材ごとの回答サマリー."""

    total_problems = serializers.IntegerField()
    answered_problems = serializers.IntegerField()
    latest_grades = serializers.ListField(
        child=serializers.IntegerField(allow_null=True)
    )


class MyProblemGroupItemSerializer(serializers.Serializer):
    """復習一覧の各アイテム."""

    problem_group_id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    difficulty = serializers.CharField()
    completed_at = serializers.CharField(allow_null=True)
    answer_summary = AnswerSummarySerializer()


class MyProblemGroupsDataSerializer(serializers.Serializer):
    """復習一覧レスポンスの data 部分."""

    items = MyProblemGroupItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class AnswerHistoryItemSerializer(serializers.Serializer):
    """小問ごとの回答履歴."""

    answer_id = serializers.IntegerField()
    answer_body = serializers.CharField()
    grade = serializers.IntegerField()
    grade_display = serializers.CharField()
    created_at = serializers.CharField()


class ProblemGroupDetailDataSerializer(serializers.Serializer):
    """題材詳細レスポンスの data 部分."""

    problem_group = ProblemGroupDetailSerializer()
    problems = ProblemSerializer(many=True)
    answers = serializers.DictField(
        child=AnswerHistoryItemSerializer(many=True),
    )


class GenerateProblemResultSerializer(serializers.Serializer):
    """問題生成結果."""

    difficulty = serializers.CharField()
    total_count = serializers.IntegerField()
    attempted_count = serializers.IntegerField()
    stock_count = serializers.IntegerField()
    shortage = serializers.IntegerField()
    generated_count = serializers.IntegerField()


class GenerateProblemDataSerializer(serializers.Serializer):
    """問題生成レスポンスの data 部分."""

    results = GenerateProblemResultSerializer(many=True)
    total_generated = serializers.IntegerField()


class RankingItemSerializer(serializers.Serializer):
    """ランキングの1件."""

    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    score = serializers.IntegerField()


class RankingDataSerializer(serializers.Serializer):
    """ランキングレスポンスの data 部分."""

    period = serializers.CharField()
    score_type = serializers.CharField()
    rankings = RankingItemSerializer(many=True)


class GradeDistributionSerializer(serializers.Serializer):
    """成績分布."""

    correct = serializers.IntegerField()
    partial = serializers.IntegerField()
    incorrect = serializers.IntegerField()


class DifficultyStatSerializer(serializers.Serializer):
    """難易度別統計."""

    count = serializers.IntegerField()
    average_grade = serializers.FloatField()


class StreakSerializer(serializers.Serializer):
    """ストリーク情報."""

    current = serializers.IntegerField()
    longest = serializers.IntegerField()


class ActivityCalendarItemSerializer(serializers.Serializer):
    """日別アクティビティ."""

    date = serializers.CharField()
    count = serializers.IntegerField()
    grade_sum = serializers.IntegerField()


class DashboardDataSerializer(serializers.Serializer):
    """ダッシュボードレスポンスの data 部分."""

    total_problem_groups = serializers.IntegerField()
    total_answers = serializers.IntegerField()
    average_grade = serializers.FloatField()
    grade_distribution = GradeDistributionSerializer()
    difficulty_stats = serializers.DictField(child=DifficultyStatSerializer())
    streak = StreakSerializer()
    activity_calendar = ActivityCalendarItemSerializer(many=True)
