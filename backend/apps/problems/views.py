"""
問題生成API エンドポイント
"""

import secrets
from django.db import transaction
from django.db.models import Max
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    GuestLimitReachedError,
    GuestAlreadyGeneratedError,
    GuestSessionNotFoundError,
    GuestTokenMismatchError,
    PermissionDeniedError,
    NotFoundError,
    GradingError,
    RequirementClarificationError,
)
from common.error_codes import ErrorCode

from .services import (
    ProblemGenerator,
    ProblemGeneratorError,
    AnswerGrader,
    AnswerGraderError,
    RequirementClarifier,
    RequirementClarifierError,
)
from .models import (
    ProblemGroup,
    Problem,
    Answer,
    Explanation,
    ModelAnswer,
    PersonalizedModelAnswer,
    RequirementItem,
    RequirementTurnLog,
)
from .ranking_service import get_ranking, Period, ScoreType
from .serializers import (
    CompleteProblemGroupDataSerializer,
    CompleteProblemGroupRequestSerializer,
    DashboardDataSerializer,
    GenerateProblemDataSerializer,
    GenerateProblemRequestSerializer,
    GradeResponseDataSerializer,
    GradeAnswerRequestSerializer,
    MyProblemGroupsDataSerializer,
    MyProblemGroupsQuerySerializer,
    ProblemGroupDetailDataSerializer,
    ProblemGroupFetchDataSerializer,
    ProblemGroupQuerySerializer,
    RequirementListDataSerializer,
    RequirementQuestionDataSerializer,
    RequirementQuestionRequestSerializer,
    RankingQuerySerializer,
    RankingDataSerializer,
)


def serialize_data(serializer_class, payload):
    """レスポンス payload を serializer 経由で整形する."""
    serializer = serializer_class(payload)
    return serializer.data


def validate_input(serializer_class, data, *, context=None):
    """入力データを serializer で検証する."""
    serializer = serializer_class(data=data, context=context or {})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class GenerateProblemView(APIView):
    """
    POST /api/v1/problem-groups/generate

    問題生成エンドポイント（バッチ専用）
    - 在庫チェック＋補充を行う
    - アクセス制限：バッチ専用API
    - 認証：X-Batch-Secretヘッダーが必要
    """

    def post(self, request):
        """
        問題を生成・補充する（バッチ専用API）

        Request Body:
            {
                "difficulties": ["easy", "medium", "hard"]  // 省略時は全難易度を処理
            }
            または
            {
                "difficulty": "easy"  // 従来形式（1つのみ）
            }

        Response (200):
            {
                "data": {
                    "results": [
                        {
                            "difficulty": "easy",
                            "total_count": 10,
                            "attempted_count": 5,
                            "stock_count": 5,
                            "shortage": 0,
                            "generated_count": 0,
                            "problem_group": { ... }  // 最後に生成した問題グループ
                        },
                        ...
                    ],
                    "total_generated": 0
                },
                "error": null
            }
        """
        from django.conf import settings
        from .models import ProblemGroupAttempt

        batch_secret = request.headers.get("X-Batch-Secret", "")
        expected_secret = getattr(settings, "BATCH_SECRET_KEY", None)

        if not expected_secret or not secrets.compare_digest(
            batch_secret, expected_secret or ""
        ):
            raise PermissionDeniedError(
                message="このAPIはバッチ専用です。直接アクセスできません。"
            )

        validated_data = validate_input(GenerateProblemRequestSerializer, request.data)
        min_stock = validated_data["min_stock"]

        # リクエストボディから難易度を取得
        difficulties_param = validated_data.get("difficulties")
        difficulty_param = validated_data.get("difficulty")

        if difficulties_param is not None:
            difficulties = difficulties_param
        elif difficulty_param is not None:
            difficulties = [difficulty_param]
        else:
            # デフォルト：全難易度を処理
            difficulties = ["easy", "medium", "hard"]

        results = []
        total_generated = 0

        for difficulty in difficulties:
            # 在庫数をカウント: 全問題数 - 解答済み問題数
            total_count = ProblemGroup.objects.filter(difficulty=difficulty).count()

            # 少なくとも1人以上が解答した問題グループの数をカウント
            attempted_count = (
                ProblemGroupAttempt.objects.filter(problem_group__difficulty=difficulty)
                .values("problem_group_id")
                .distinct()
                .count()
            )

            stock_count = total_count - attempted_count

            generated_count = 0
            shortage = max(0, min_stock - stock_count)

            if shortage > 0:
                for _ in range(shortage):
                    try:
                        generator = ProblemGenerator()
                        problem_group, problems, _ = generator.generate(
                            difficulty=difficulty
                        )
                        generated_count += 1
                        total_generated += 1
                    except ProblemGeneratorError:
                        continue

            results.append(
                {
                    "difficulty": difficulty,
                    "total_count": total_count + generated_count,
                    "attempted_count": attempted_count,
                    "stock_count": stock_count + generated_count,
                    "shortage": shortage,
                    "generated_count": generated_count,
                }
            )

        return Response(
            {
                "data": serialize_data(
                    GenerateProblemDataSerializer,
                    {
                        "results": results,
                        "total_generated": total_generated,
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class GetProblemGroupView(APIView):
    """
    GET /api/v1/problem-groups

    新規問題取得エンドポイント
    - ログインユーザー：未解答の問題を1つ払い出し
    - ゲストユーザー：ランダムに1つ払い出し（1問のみ）
    """

    def get(self, request):
        """
        難易度を指定して、新規問題を取得する

        Query Parameters:
            difficulty (required): easy | medium | hard

        Response (200):
            {
                "data": {
                    "kind": "persisted" | "guest",
                    "problem_group": { ... },
                    "problems": [ ... ],
                    "guest_token": "..." (ゲストのみ)
                },
                "error": null
            }
        """
        import secrets
        from .models import ProblemGroupAttempt

        validated_query = validate_input(
            ProblemGroupQuerySerializer,
            request.query_params,
        )
        difficulty = validated_query["difficulty"]

        if request.user.is_authenticated:
            # 既に問題取得済みかチェック
            if request.session.get("current_problem_group_id"):
                problem_group_id = request.session.get("current_problem_group_id")
                try:
                    problem_group = ProblemGroup.objects.get(
                        problem_group_id=problem_group_id
                    )
                    problems = list(
                        problem_group.problems.all().order_by("order_index")
                    )

                    return Response(
                        {
                            "data": serialize_data(
                                ProblemGroupFetchDataSerializer,
                                {
                                    "kind": "persisted",
                                    "problem_group": {
                                        "problem_group_id": problem_group.problem_group_id,
                                        "title": problem_group.title,
                                        "description": problem_group.description,
                                        "difficulty": problem_group.difficulty,
                                    },
                                    "problems": [
                                        {
                                            "problem_id": p.problem_id,
                                            "problem_group_id": problem_group.problem_group_id,
                                            "order_index": p.order_index,
                                            "problem_type": p.problem_type,
                                            "problem_body": p.problem_body,
                                        }
                                        for p in problems
                                    ],
                                },
                            ),
                            "error": None,
                        },
                        status=status.HTTP_200_OK,
                    )
                except ProblemGroup.DoesNotExist:
                    # セッションのデータが無効な場合はクリアして新規生成に進む
                    del request.session["current_problem_group_id"]

            attempted_ids = ProblemGroupAttempt.objects.filter(
                user=request.user
            ).values_list("problem_group_id", flat=True)

            problem_group = (
                ProblemGroup.objects.filter(difficulty=difficulty)
                .exclude(problem_group_id__in=attempted_ids)
                .order_by("created_at")
                .first()
            )

            if not problem_group:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"難易度 {difficulty} の問題の上限に達しました。新しい問題を解くには時間をおいてから再度お試しください。",
                )

            request.session["current_problem_group_id"] = problem_group.problem_group_id

            problems = list(problem_group.problems.all().order_by("order_index"))

            return Response(
                {
                    "data": serialize_data(
                        ProblemGroupFetchDataSerializer,
                        {
                            "kind": "persisted",
                            "problem_group": {
                                "problem_group_id": problem_group.problem_group_id,
                                "title": problem_group.title,
                                "description": problem_group.description,
                                "difficulty": problem_group.difficulty,
                            },
                            "problems": [
                                {
                                    "problem_id": p.problem_id,
                                    "problem_group_id": problem_group.problem_group_id,
                                    "order_index": p.order_index,
                                    "problem_type": p.problem_type,
                                    "problem_body": p.problem_body,
                                }
                                for p in problems
                            ],
                        },
                    ),
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        # ゲストユーザーの場合
        else:
            if request.session.get("guest_completed"):
                raise GuestLimitReachedError(
                    message="ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。"
                )

            if request.session.get("guest_problem_token"):
                raise GuestAlreadyGeneratedError(
                    message="ゲストユーザーは既に問題を取得済みです。先に回答を完了してください。"
                )

            problem_group = (
                ProblemGroup.objects.filter(difficulty=difficulty)
                .order_by("created_at")
                .first()
            )

            if not problem_group:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"難易度 {difficulty} の問題が在庫にありません。",
                )

            guest_token = secrets.token_urlsafe(32)
            request.session["guest_problem_token"] = guest_token
            request.session["current_problem_group_id"] = problem_group.problem_group_id

            problems = list(problem_group.problems.all().order_by("order_index"))

            return Response(
                {
                    "data": serialize_data(
                        ProblemGroupFetchDataSerializer,
                        {
                            "kind": "guest",
                            "guest_token": guest_token,
                            "problem_group": {
                                "problem_group_id": problem_group.problem_group_id,
                                "title": problem_group.title,
                                "description": problem_group.description,
                                "difficulty": problem_group.difficulty,
                            },
                            "problems": [
                                {
                                    "problem_id": p.problem_id,
                                    "problem_group_id": problem_group.problem_group_id,
                                    "order_index": p.order_index,
                                    "problem_type": p.problem_type,
                                    "problem_body": p.problem_body,
                                }
                                for p in problems
                            ],
                        },
                    ),
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )


class RequirementQuestionView(APIView):
    """
    POST /api/v1/problem-groups/{problem_group_id}/requirements/questions

    要件明確化の問い合わせを受け付け、原文ログと構造化データを保存する。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, problem_group_id: int):
        validated_data = validate_input(
            RequirementQuestionRequestSerializer,
            request.data,
        )

        current_pg_id = request.session.get("current_problem_group_id")
        if current_pg_id != problem_group_id:
            raise PermissionDeniedError(
                message="この題材は現在のセッションで進行中ではありません"
            )

        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_GROUP_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        try:
            clarifier = RequirementClarifier()
            turn_log, requirement_items = clarifier.clarify(
                problem_group=problem_group,
                user=request.user,
                question=validated_data["question"],
            )
        except RequirementClarifierError as e:
            raise RequirementClarificationError(message=str(e))

        return Response(
            {
                "data": serialize_data(
                    RequirementQuestionDataSerializer,
                    {
                        "turn": {
                            "id": turn_log.id,
                            "turn_no": turn_log.turn_no,
                            "user_question": turn_log.user_question,
                            "ai_answer": turn_log.ai_answer,
                        },
                        "requirement_items": [
                            {
                                "id": item.id,
                                "subject": item.subject,
                                "predicate": item.predicate,
                                "object_value": item.object_value,
                                "detail_text": item.detail_text,
                            }
                            for item in requirement_items
                        ],
                    },
                ),
                "error": None,
            },
            status=status.HTTP_201_CREATED,
        )


class RequirementListView(APIView):
    """
    GET /api/v1/problem-groups/{problem_group_id}/requirements

    指定題材に対するログインユーザーの要件問い合わせ履歴を返す。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, problem_group_id: int):
        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_GROUP_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        turn_logs = list(
            RequirementTurnLog.objects.filter(
                problem_group=problem_group,
                user=request.user,
            ).order_by("turn_no")
        )
        requirement_items = list(
            RequirementItem.objects.filter(
                problem_group=problem_group,
                user=request.user,
            ).order_by("id")
        )

        return Response(
            {
                "data": serialize_data(
                    RequirementListDataSerializer,
                    {
                        "turn_logs": [
                            {
                                "id": turn.id,
                                "turn_no": turn.turn_no,
                                "user_question": turn.user_question,
                                "ai_answer": turn.ai_answer,
                            }
                            for turn in turn_logs
                        ],
                        "requirement_items": [
                            {
                                "id": item.id,
                                "subject": item.subject,
                                "predicate": item.predicate,
                                "object_value": item.object_value,
                                "detail_text": item.detail_text,
                            }
                            for item in requirement_items
                        ],
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class GradeAnswerView(APIView):
    """
    POST /api/v1/problem-groups/grade

    一括採点エンドポイント
    - ログインユーザー: problem_group_id + answers 配列で全問を一括採点、DBに保存
    - ゲストユーザー: guest_token + answers 配列で全問を一括採点、保存しない
    """

    GRADE_DISPLAY_MAP = {0: "×", 1: "△", 2: "○"}

    @staticmethod
    def _build_requirement_section(requirement_items: list[RequirementItem]) -> str:
        """採点用に追加要件セクションを組み立てる."""
        if not requirement_items:
            return ""

        requirement_lines = []
        for item in requirement_items:
            requirement_lines.append(
                (
                    f"- {item.detail_text} "
                    f"(subject={item.subject}, predicate={item.predicate}, "
                    f"object_value={item.object_value})"
                )
            )

        return "\n\n## 追加要件\n" + "\n".join(requirement_lines)

    @classmethod
    def _build_grading_problem_body(
        cls, problem: Problem, requirement_items: list[RequirementItem]
    ) -> str:
        """問題文と追加要件を結合し、採点AIへ渡す本文を組み立てる."""
        return problem.problem_body + cls._build_requirement_section(requirement_items)

    @staticmethod
    def _save_personalized_model_answer(
        *,
        problem: Problem,
        problem_group: ProblemGroup,
        user,
        model_answer: str,
    ) -> PersonalizedModelAnswer:
        """採点時に生成された個別模範解答を version 管理で保存する."""
        next_version = (
            PersonalizedModelAnswer.objects.filter(
                problem=problem,
                problem_group=problem_group,
                user=user,
            ).aggregate(max_version=Max("version"))["max_version"]
            or 0
        ) + 1

        return PersonalizedModelAnswer.objects.create(
            problem=problem,
            problem_group=problem_group,
            user=user,
            version=next_version,
            model_answer=model_answer,
        )

    def post(self, request):
        """
        回答を一括採点する

        Request Body (ログイン):
            {
                "problem_group_id": 123,
                "answers": [
                    {"problem_id": 1, "answer_body": "CREATE TABLE ..."},
                    {"problem_id": 2, "answer_body": "def create_post(...): ..."}
                ]
            }

        Request Body (ゲスト):
            {
                "guest_token": "opaque-token",
                "answers": [
                    {"problem_id": 1, "answer_body": "CREATE TABLE ..."},
                    {"problem_id": 2, "answer_body": "def create_post(...): ..."}
                ]
            }

        Response (200):
            {
                "data": {
                    "results": [
                        {
                            "problem_ref": {"problem_id": 1, "order_index": 1},
                            "problem_type": "db",
                            "grade": 2,
                            "grade_display": "○",
                            "explanation": {"version": 1, "explanation_body": "..."},
                            "answer_id": 456  // ログインユーザーのみ
                        },
                        ...
                    ]
                },
                "error": null
            }
        """
        validated_data = validate_input(
            GradeAnswerRequestSerializer,
            request.data,
            context={"request": request},
        )
        problem_group_id = validated_data.get("problem_group_id")
        guest_token = validated_data.get("guest_token")
        answers = validated_data["answers"]

        if not request.user.is_authenticated and request.session.get("guest_completed"):
            raise GuestLimitReachedError(
                message="ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。"
            )

        if request.user.is_authenticated:
            return self._handle_authenticated_user(request, problem_group_id, answers)

        return self._handle_guest_user(request, guest_token, answers)

    def _handle_authenticated_user(self, request, problem_group_id: int, answers: list):
        """
        ログインユーザー向けの一括採点処理

        Args:
            request: リクエストオブジェクト
            problem_group_id: 問題グループID
            answers: 回答リスト [{"problem_id", "answer_body"}, ...]

        Returns:
            Response: 採点結果のレスポンス
        """
        current_pg_id = request.session.get("current_problem_group_id")
        if current_pg_id != problem_group_id:
            raise PermissionDeniedError(
                message="この題材は現在のセッションで進行中ではありません"
            )

        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        problems = list(
            Problem.objects.filter(problem_group=problem_group).order_by("order_index")
        )
        requirement_items = list(
            RequirementItem.objects.filter(
                problem_group=problem_group,
                user=request.user,
            ).order_by("id")
        )

        problem_map = {p.problem_id: p for p in problems}

        latest_model_answers = (
            ModelAnswer.objects.filter(problem__in=problems)
            .order_by("problem_id", "-version")
            .distinct("problem_id")
        )
        latest_model_answer_map = {ma.problem_id: ma for ma in latest_model_answers}

        for answer in answers:
            if answer["problem_id"] not in problem_map:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"問題ID {answer['problem_id']} が見つかりません",
                )

        problems_with_answers = []
        for answer in answers:
            problem = problem_map[answer["problem_id"]]
            problems_with_answers.append(
                {
                    "order_index": problem.order_index,
                    "problem_type": problem.problem_type,
                    "problem_body": self._build_grading_problem_body(
                        problem,
                        requirement_items,
                    ),
                    "answer_body": answer["answer_body"],
                    "problem_id": problem.problem_id,
                }
            )

        try:
            grader = AnswerGrader()
            grading_results = grader.grade_batch(problems_with_answers)
        except AnswerGraderError as e:
            raise GradingError(message=str(e))

        result_map = {r["order_index"]: r for r in grading_results}

        results = []
        with transaction.atomic():
            for item in problems_with_answers:
                problem = problem_map[item["problem_id"]]
                grading_result = result_map[item["order_index"]]

                answer_record = Answer.objects.create(
                    problem=problem,
                    user=request.user,
                    answer_body=item["answer_body"],
                    grade=grading_result["grade"],
                )

                Explanation.objects.create(
                    answer=answer_record,
                    version=answer_record.version,
                    explanation_body=grading_result["explanation"],
                )

                personalized_model_answer = None
                if requirement_items:
                    personalized_model_answer = self._save_personalized_model_answer(
                        problem=problem,
                        problem_group=problem_group,
                        user=request.user,
                        model_answer=grading_result["model_answer"],
                    )

                model_answer_obj = (
                    personalized_model_answer
                    or latest_model_answer_map.get(problem.problem_id)
                )
                results.append(
                    {
                        "problem_ref": {
                            "problem_id": problem.problem_id,
                            "order_index": problem.order_index,
                        },
                        "problem_type": problem.problem_type,
                        "grade": grading_result["grade"],
                        "grade_display": self.GRADE_DISPLAY_MAP.get(
                            grading_result["grade"], "×"
                        ),
                        "explanation": {
                            "version": answer_record.version,
                            "explanation_body": grading_result["explanation"],
                        },
                        "model_answer": {
                            "version": model_answer_obj.version,
                            "model_answer": model_answer_obj.model_answer,
                        }
                        if model_answer_obj
                        else None,
                        "answer_id": answer_record.answer_id,
                    }
                )

        results.sort(key=lambda x: x["problem_ref"]["order_index"])

        return Response(
            {
                "data": serialize_data(
                    GradeResponseDataSerializer,
                    {"results": results},
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_guest_user(self, request, guest_token: str, answers: list):
        """
        ゲストユーザー向けの一括採点処理

        Args:
            request: リクエストオブジェクト
            guest_token: ゲストトークン
            answers: 回答リスト [{"order_index", "answer_body"}, ...]

        Returns:
            Response: 採点結果のレスポンス
        """
        session_token = request.session.get("guest_problem_token")
        if not session_token:
            raise GuestSessionNotFoundError(
                message="ゲストセッションが見つかりません。先に問題を生成してください。"
            )
        if session_token != guest_token:
            raise GuestTokenMismatchError(message="ゲストトークンが一致しません")

        current_pg_id = request.session.get("current_problem_group_id")
        if not current_pg_id:
            raise GuestSessionNotFoundError(
                message="題材情報が見つかりません。先に問題を生成してください。"
            )

        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=current_pg_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_GROUP_NOT_FOUND,
                message=f"問題グループID {current_pg_id} が見つかりません",
            )

        problems = list(
            Problem.objects.filter(problem_group=problem_group).order_by("order_index")
        )
        problem_map = {p.problem_id: p for p in problems}

        latest_model_answers = (
            ModelAnswer.objects.filter(problem__in=problems)
            .order_by("problem_id", "-version")
            .distinct("problem_id")
        )
        latest_model_answer_map = {ma.problem_id: ma for ma in latest_model_answers}

        for answer in answers:
            if answer["problem_id"] not in problem_map:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"問題ID {answer['problem_id']} が見つかりません",
                )

        problems_with_answers = []
        for answer in answers:
            problem = problem_map[answer["problem_id"]]
            problems_with_answers.append(
                {
                    "order_index": problem.order_index,
                    "problem_type": problem.problem_type,
                    "problem_body": problem.problem_body,
                    "answer_body": answer["answer_body"],
                    "problem_id": problem.problem_id,
                }
            )

        try:
            grader = AnswerGrader()
            grading_results = grader.grade_batch(problems_with_answers)
        except AnswerGraderError as e:
            raise GradingError(message=str(e))

        result_map = {r["order_index"]: r for r in grading_results}

        results = []
        for item in problems_with_answers:
            grading_result = result_map[item["order_index"]]
            model_answer_obj = latest_model_answer_map.get(item["problem_id"])

            results.append(
                {
                    "problem_ref": {
                        "problem_id": item["problem_id"],
                        "order_index": item["order_index"],
                    },
                    "problem_type": item["problem_type"],
                    "grade": grading_result["grade"],
                    "grade_display": self.GRADE_DISPLAY_MAP.get(
                        grading_result["grade"], "×"
                    ),
                    "explanation": {
                        "version": 1,
                        "explanation_body": grading_result["explanation"],
                    },
                    "model_answer": {
                        "version": model_answer_obj.version,
                        "model_answer": model_answer_obj.model_answer,
                    }
                    if model_answer_obj
                    else None,
                }
            )

        results.sort(key=lambda x: x["problem_ref"]["order_index"])

        return Response(
            {
                "data": serialize_data(
                    GradeResponseDataSerializer,
                    {"results": results},
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class CompleteProblemGroupView(APIView):
    """
    POST /api/v1/problem-groups/{problem_group_id}/complete

    題材の完了エンドポイント
    - ログインユーザー: attempts に upsert、セッションの current_problem_group_id を削除
    - ゲストユーザー: guest_token 検証、guest_completed=True を設定し、トークンと current_problem_group_id をクリア
    """

    def post(self, request, problem_group_id: int):
        from .models import ProblemGroupAttempt

        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_GROUP_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        if request.user.is_authenticated:
            current_id = request.session.get("current_problem_group_id")
            if current_id != problem_group_id:
                raise PermissionDeniedError(
                    message="この題材は現在のセッションで進行中ではありません"
                )

            ProblemGroupAttempt.objects.get_or_create(
                problem_group=problem_group,
                user=request.user,
            )

            if "current_problem_group_id" in request.session:
                del request.session["current_problem_group_id"]
            request.session.modified = True

            return Response(
                {
                    "data": serialize_data(
                        CompleteProblemGroupDataSerializer,
                        {"ok": True},
                    ),
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        validated_data = validate_input(
            CompleteProblemGroupRequestSerializer,
            request.data,
            context={"request": request},
        )
        guest_token = validated_data.get("guest_token")

        session_token = request.session.get("guest_problem_token")
        if not session_token:
            raise GuestSessionNotFoundError(
                message="ゲストセッションが見つかりません。先に問題を生成してください。"
            )
        if session_token != guest_token:
            raise GuestTokenMismatchError(message="ゲストトークンが一致しません")

        current_pg_id = request.session.get("current_problem_group_id")
        if current_pg_id != problem_group_id:
            raise PermissionDeniedError(
                message="この題材は現在のセッションで進行中ではありません"
            )

        request.session["guest_completed"] = True
        if "guest_problem_token" in request.session:
            del request.session["guest_problem_token"]
        if "current_problem_group_id" in request.session:
            del request.session["current_problem_group_id"]
        request.session.modified = True

        return Response(
            {
                "data": serialize_data(
                    CompleteProblemGroupDataSerializer,
                    {"ok": True},
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class MyProblemGroupsView(APIView):
    """
    GET /api/v1/problem-groups/mine

    自分が生成した題材一覧を取得
    - ログインユーザーのみ
    - 難易度・モードでフィルタリング可能
    - created_at 降順で返却
    """

    def get(self, request):
        """
        自分の題材一覧を取得する

        Query Parameters:
            difficulty: "easy" | "medium" | "hard" (optional)
            mode: "db_only" | "api_only" | "both" (optional)
            cursor: ページネーション用カーソル (optional, 未実装)

        Response (200):
            {
                "data": {
                    "items": [
                        {
                            "problem_group_id": 123,
                            "title": "SNSアプリ",
                            "description": "...",
                            "difficulty": "easy",
                            "app_scale": "small",
                            "mode": "both",
                            "created_at": "...",
                            "answer_summary": {
                                "total_problems": 2,
                                "answered_problems": 2,
                                "latest_grades": [2, 1]
                            }
                        }
                    ],
                    "next_cursor": null
                },
                "error": null
            }
        """
        if not request.user.is_authenticated:
            raise PermissionDeniedError(
                message="復習機能を利用するにはログインが必要です"
            )

        validated_query = validate_input(
            MyProblemGroupsQuerySerializer,
            request.query_params,
        )

        filters = {}
        difficulty = validated_query.get("difficulty")
        if difficulty:
            filters["difficulty"] = difficulty

        from .models import ProblemGroupAttempt

        attempted_ids = ProblemGroupAttempt.objects.filter(
            user=request.user
        ).values_list("problem_group_id", flat=True)
        answered_ids = Answer.objects.filter(user=request.user).values_list(
            "problem__problem_group_id", flat=True
        )
        target_ids = set(attempted_ids) | set(answered_ids)

        if not target_ids:
            return Response(
                {
                    "data": serialize_data(
                        MyProblemGroupsDataSerializer,
                        {
                            "items": [],
                            "next_cursor": None,
                        },
                    ),
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        from django.db.models import Max, Prefetch

        problem_groups_with_attempts = (
            ProblemGroup.objects.filter(
                problem_group_id__in=list(target_ids), **filters
            )
            .prefetch_related(
                Prefetch("problems", queryset=Problem.objects.order_by("order_index")),
                "attempts",
            )
            .annotate(attempt_date=Max("attempts__created_at"))
            .order_by("-attempt_date")
        )

        all_problem_ids_set = set()
        for pg in problem_groups_with_attempts:
            all_problem_ids_set.update(p.problem_id for p in pg.problems.all())

        latest_answers = (
            Answer.objects.filter(
                problem_id__in=list(all_problem_ids_set), user=request.user
            )
            .order_by("problem_id", "-created_at")
            .distinct("problem_id")
        )

        answer_map = {answer.problem_id: answer for answer in latest_answers}

        latest_answer_dates = (
            Answer.objects.filter(
                problem__problem_group_id__in=list(target_ids), user=request.user
            )
            .values("problem__problem_group_id")
            .annotate(latest_created_at=Max("created_at"))
        )
        answer_date_map = {
            item["problem__problem_group_id"]: item["latest_created_at"]
            for item in latest_answer_dates
        }

        items = []
        for pg in problem_groups_with_attempts:
            problems = list(pg.problems.all())
            total_problems = len(problems)

            latest_grades = []
            answered_count = 0
            for problem in problems:
                latest_answer = answer_map.get(problem.problem_id)
                if latest_answer:
                    latest_grades.append(latest_answer.grade)
                    answered_count += 1
                else:
                    latest_grades.append(None)

            completion_date = pg.attempt_date
            if not completion_date:
                completion_date = answer_date_map.get(pg.problem_group_id)

            items.append(
                {
                    "problem_group_id": pg.problem_group_id,
                    "title": pg.title,
                    "description": pg.description,
                    "difficulty": pg.difficulty,
                    "completed_at": completion_date.isoformat()
                    if completion_date
                    else None,
                    "answer_summary": {
                        "total_problems": total_problems,
                        "answered_problems": answered_count,
                        "latest_grades": latest_grades,
                    },
                }
            )

        return Response(
            {
                "data": serialize_data(
                    MyProblemGroupsDataSerializer,
                    {
                        "items": items,
                        "next_cursor": None,
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class ProblemGroupDetailView(APIView):
    """
    GET /api/v1/problem-groups/{problem_group_id}

    題材詳細を取得
    - ログインユーザーのみ
    """

    def get(self, request, problem_group_id: int):
        """
        題材詳細を取得する

        Response (200):
            {
                "data": {
                    "problem_group": {...},
                    "problems": [...],
                    "answers": {
                        "problem_id": [{"answer_id", "answer_body", "grade", "grade_display", "created_at"}, ...]
                    }
                },
                "error": null
            }
        """
        if not request.user.is_authenticated:
            raise PermissionDeniedError(
                message="復習機能を利用するにはログインが必要です"
            )

        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        start_flag = request.query_params.get("start")
        if start_flag == "true" and request.user.is_authenticated:
            request.session["current_problem_group_id"] = problem_group.problem_group_id
            request.session.modified = True

        problems = list(problem_group.problems.all().order_by("order_index"))

        problem_ids = [p.problem_id for p in problems]
        all_user_answers = Answer.objects.filter(
            problem_id__in=problem_ids, user=request.user
        ).order_by("problem_id", "-created_at")

        grade_display_map = {0: "×", 1: "△", 2: "○"}
        answers_by_problem = {pid: [] for pid in problem_ids}

        for answer in all_user_answers:
            answers_by_problem[answer.problem_id].append(
                {
                    "answer_id": answer.answer_id,
                    "answer_body": answer.answer_body,
                    "grade": answer.grade,
                    "grade_display": grade_display_map.get(answer.grade, "×"),
                    "created_at": answer.created_at.isoformat(),
                }
            )

        from .models import ProblemGroupAttempt

        attempt = ProblemGroupAttempt.objects.filter(
            problem_group=problem_group, user=request.user
        ).first()
        completed_at = attempt.created_at.isoformat() if attempt else None

        return Response(
            {
                "data": serialize_data(
                    ProblemGroupDetailDataSerializer,
                    {
                        "problem_group": {
                            "problem_group_id": problem_group.problem_group_id,
                            "title": problem_group.title,
                            "description": problem_group.description,
                            "difficulty": problem_group.difficulty,
                            "created_at": problem_group.created_at.isoformat(),
                            "completed_at": completed_at,
                        },
                        "problems": [
                            {
                                "problem_id": p.problem_id,
                                "problem_type": p.problem_type,
                                "order_index": p.order_index,
                                "problem_body": p.problem_body,
                            }
                            for p in problems
                        ],
                        "answers": answers_by_problem,
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class RankingView(APIView):
    """
    GET /api/v1/rankings

    ランキング取得エンドポイント
    - 期間（period）とスコア計算方式（score_type）を指定可能
    - 認証不要（誰でも閲覧可能）
    """

    def get(self, request):
        """
        ランキングを取得する

        Query Parameters:
            period: "daily" | "weekly" | "monthly" | "all" (default: "daily")
            score_type: "problem_count" | "correct_count" | "grade_sum" (default: "problem_count")
            limit: 1-100 (default: 5)

        Response (200):
            {
                "data": {
                    "period": "daily",
                    "score_type": "problem_count",
                    "rankings": [
                        {"rank": 1, "user_id": 1, "name": "Alice", "score": 15},
                        ...
                    ]
                },
                "error": null
            }
        """
        validated_query = validate_input(
            RankingQuerySerializer,
            request.query_params,
        )
        period_str = validated_query["period"]
        score_type_str = validated_query["score_type"]
        limit = validated_query["limit"]

        period = Period(period_str)
        score_type = ScoreType(score_type_str)

        rankings = get_ranking(period=period, score_type=score_type, limit=limit)

        rankings_data = [
            {
                "rank": entry.rank,
                "user_id": entry.user_id,
                "name": entry.name,
                "score": entry.score,
            }
            for entry in rankings
        ]

        return Response(
            {
                "data": serialize_data(
                    RankingDataSerializer,
                    {
                        "period": period_str,
                        "score_type": score_type_str,
                        "rankings": rankings_data,
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class DashboardView(APIView):
    """
    GET /api/v1/dashboard

    ダッシュボード用の統計データを取得
    - ログインユーザーのみ
    """

    def get(self, request):
        """
        ダッシュボードデータを取得する

        Response (200):
            {
                "data": {
                    "total_problems": 10,
                    "total_answers": 15,
                    "average_grade": 1.5,
                    "grade_distribution": {"correct": 5, "partial": 7, "incorrect": 3},
                    "difficulty_stats": {
                        "easy": {"count": 5, "average_grade": 1.8},
                        "medium": {"count": 3, "average_grade": 1.2},
                        "hard": {"count": 2, "average_grade": 1.0}
                    },
                    "mode_stats": {
                        "db_only": {"count": 4, "average_grade": 1.5},
                        "api_only": {"count": 3, "average_grade": 1.3},
                        "both": {"count": 3, "average_grade": 1.7}
                    },
                    "streak": {
                        "current": 3,
                        "longest": 7
                    },
                    "activity_calendar": [
                        {"date": "2024-12-01", "count": 2, "grade_sum": 3},
                        ...
                    ]
                },
                "error": null
            }
        """
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg, Count, Sum
        from django.db.models.functions import TruncDate

        if not request.user.is_authenticated:
            raise PermissionDeniedError(
                message="ダッシュボードを利用するにはログインが必要です"
            )

        user = request.user

        # 1. 基本統計
        user_answers = Answer.objects.filter(user=user)
        total_answers = user_answers.count()

        # 解いた題材数（ユニークな problem_group）
        answered_problem_groups = (
            user_answers.values("problem__problem_group").distinct().count()
        )

        # 平均スコア
        avg_grade = user_answers.aggregate(avg=Avg("grade"))["avg"] or 0

        # 成績分布
        grade_counts = user_answers.values("grade").annotate(count=Count("grade"))
        grade_distribution = {"correct": 0, "partial": 0, "incorrect": 0}
        for gc in grade_counts:
            if gc["grade"] == 2:
                grade_distribution["correct"] = gc["count"]
            elif gc["grade"] == 1:
                grade_distribution["partial"] = gc["count"]
            elif gc["grade"] == 0:
                grade_distribution["incorrect"] = gc["count"]

        # 2. 難易度別統計
        difficulty_stats = {}
        for diff in ["easy", "medium", "hard"]:
            diff_answers = user_answers.filter(problem__problem_group__difficulty=diff)
            count = diff_answers.count()
            avg = diff_answers.aggregate(avg=Avg("grade"))["avg"] or 0
            difficulty_stats[diff] = {
                "count": count,
                "average_grade": round(avg, 2),
            }

        # 3. ストリーク計算
        # 日別のアクティビティを取得
        daily_activity = (
            user_answers.annotate(date=TruncDate("created_at"))
            .values("date")
            .distinct()
            .order_by("-date")
        )
        activity_dates = set(d["date"] for d in daily_activity)

        today = timezone.now().date()
        current_streak = 0
        longest_streak = 0
        temp_streak = 0

        # 現在のストリークを計算（今日または昨日から連続している日数）
        check_date = today
        if check_date not in activity_dates:
            check_date = today - timedelta(days=1)

        while check_date in activity_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        # 最長ストリークを計算
        if activity_dates:
            sorted_dates = sorted(activity_dates)
            temp_streak = 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                    temp_streak += 1
                else:
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1
            longest_streak = max(longest_streak, temp_streak)

        # 4. カレンダーヒートマップ用データ（過去90日）
        ninety_days_ago = today - timedelta(days=90)
        calendar_data = (
            user_answers.filter(created_at__date__gte=ninety_days_ago)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("answer_id"), grade_sum=Sum("grade"))
            .order_by("date")
        )

        activity_calendar = [
            {
                "date": entry["date"].isoformat(),
                "count": entry["count"],
                "grade_sum": entry["grade_sum"] or 0,
            }
            for entry in calendar_data
        ]

        return Response(
            {
                "data": serialize_data(
                    DashboardDataSerializer,
                    {
                        "total_problem_groups": answered_problem_groups,
                        "total_answers": total_answers,
                        "average_grade": round(avg_grade, 2),
                        "grade_distribution": grade_distribution,
                        "difficulty_stats": difficulty_stats,
                        "streak": {
                            "current": current_streak,
                            "longest": longest_streak,
                        },
                        "activity_calendar": activity_calendar,
                    },
                ),
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
