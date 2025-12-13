"""
問題生成API エンドポイント
"""

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    ValidationError,
    GuestLimitReachedError,
    GuestAlreadyGeneratedError,
    GuestSessionNotFoundError,
    GuestTokenMismatchError,
    PermissionDeniedError,
    NotFoundError,
    GenerationError,
    GradingError,
)
from common.error_codes import ErrorCode

from .services import (
    ProblemGenerator,
    ProblemGeneratorError,
    AnswerGrader,
    AnswerGraderError,
)
from .models import ProblemGroup, Problem, Answer

# answer_body の長さ制限（約10KB）
MAX_ANSWER_BODY_LENGTH = 10000


class GenerateProblemView(APIView):
    """
    POST /api/v1/problem-groups/generate

    問題生成エンドポイント
    - ログインユーザー: DB保存して永続化
    - ゲストユーザー: 一時データとして返す（1問のみ）
    """

    def post(self, request):
        """
        問題を生成する

        Request Body:
            {
                "difficulty": "easy" | "medium" | "hard",
                "app_scale": "small" | "medium" | "large",
                "mode": "db_only" | "api_only" | "both"
            }

        Response (200):
            {
                "data": {
                    "kind": "persisted" | "guest",
                    "problem_group": { ... },
                    "problems": [ ... ],
                    "guest_token": "..." (ゲストの場合のみ)
                },
                "error": null
            }
        """
        # リクエストパラメータ取得
        difficulty = request.data.get("difficulty")
        app_scale = request.data.get("app_scale")
        mode = request.data.get("mode")

        # バリデーション
        if not difficulty or difficulty not in ["easy", "medium", "hard"]:
            raise ValidationError(
                message="difficulty は easy, medium, hard のいずれかを指定してください"
            )

        if not app_scale or app_scale not in ["small", "medium", "large"]:
            raise ValidationError(
                message="app_scale は small, medium, large のいずれかを指定してください"
            )

        if not mode or mode not in ["db_only", "api_only", "both"]:
            raise ValidationError(
                message="mode は db_only, api_only, both のいずれかを指定してください"
            )

        # ゲスト制限チェック
        if not request.user.is_authenticated:
            # ゲストが既に採点完了している場合
            if request.session.get("guest_completed"):
                raise GuestLimitReachedError(
                    message="ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。"
                )

            # ゲストが既に問題を生成している場合
            if request.session.get("guest_problem_token"):
                raise GuestAlreadyGeneratedError(
                    message="ゲストユーザーは既に問題を生成しています。先に回答を提出してください。"
                )

        # 問題生成
        try:
            generator = ProblemGenerator()
            user = request.user if request.user.is_authenticated else None
            problem_group, problems, response_data = generator.generate(
                difficulty=difficulty,
                app_scale=app_scale,
                mode=mode,
                user=user,
            )

            # ゲストの場合、セッションにトークンを保存
            if not request.user.is_authenticated:
                request.session["guest_problem_token"] = response_data["guest_token"]
                # 生成データもセッションに保存（採点時に使用）
                request.session["guest_problem_data"] = response_data

            return Response(
                {
                    "data": response_data,
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        except ProblemGeneratorError as e:
            raise GenerationError(message=str(e))


class GradeAnswerView(APIView):
    """
    POST /api/v1/problem-groups/grade

    一括採点エンドポイント
    - ログインユーザー: problem_group_id + answers 配列で全問を一括採点、DBに保存
    - ゲストユーザー: guest_token + answers 配列で全問を一括採点、保存しない
    """

    # grade → 表示文字列のマッピング
    GRADE_DISPLAY_MAP = {0: "×", 1: "△", 2: "○"}

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
                    {"order_index": 1, "answer_body": "CREATE TABLE ..."},
                    {"order_index": 2, "answer_body": "def create_post(...): ..."}
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
                            "solution": {"version": 1, "solution_body": "...", "explanation": "..."},
                            "answer_id": 456  // ログインユーザーのみ
                        },
                        ...
                    ]
                },
                "error": null
            }
        """
        # リクエストパラメータ取得
        problem_group_id = request.data.get("problem_group_id")
        guest_token = request.data.get("guest_token")
        answers = request.data.get("answers")

        # answers バリデーション
        if not answers or not isinstance(answers, list) or len(answers) == 0:
            raise ValidationError(message="answers は1件以上の配列である必要があります")

        # XOR入力ルールチェック（problem_group_id と guest_token は排他）
        is_authenticated = request.user.is_authenticated
        has_problem_group_id = problem_group_id is not None
        has_guest_token = guest_token is not None

        # ログインユーザーの場合
        if is_authenticated:
            if not has_problem_group_id:
                raise ValidationError(
                    message="ログインユーザーは problem_group_id が必須です"
                )
            if has_guest_token:
                raise ValidationError(
                    message="ログインユーザーは guest_token を指定できません"
                )

        # ゲストユーザーの場合
        else:
            if has_problem_group_id:
                raise ValidationError(
                    message="ゲストユーザーは problem_group_id を指定できません"
                )
            if not has_guest_token:
                raise ValidationError(message="ゲストユーザーは guest_token が必須です")

            # ゲスト制限チェック（採点完了済みの場合は拒否）
            if request.session.get("guest_completed"):
                raise GuestLimitReachedError(
                    message="ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。"
                )

        # 各 answer のバリデーション
        self._validate_answers(answers, is_authenticated)

        # ログインユーザー向け処理
        if is_authenticated:
            return self._handle_authenticated_user(request, problem_group_id, answers)

        # ゲストユーザー向け処理
        return self._handle_guest_user(request, guest_token, answers)

    def _validate_answers(self, answers: list, is_authenticated: bool) -> None:
        """
        answers 配列の各要素をバリデーションする

        Args:
            answers: 回答リスト
            is_authenticated: ログインユーザーかどうか

        Raises:
            ValidationError: バリデーションエラー
        """
        key_field = "problem_id" if is_authenticated else "order_index"
        seen_keys = set()

        for idx, answer in enumerate(answers):
            # answer_body チェック
            answer_body = answer.get("answer_body")
            if (
                not answer_body
                or not isinstance(answer_body, str)
                or not answer_body.strip()
            ):
                raise ValidationError(message=f"answers[{idx}]: answer_body は必須です")

            # answer_body 長さチェック
            if len(answer_body) > MAX_ANSWER_BODY_LENGTH:
                raise ValidationError(
                    message=f"answers[{idx}]: 回答は{MAX_ANSWER_BODY_LENGTH}文字以下である必要があります"
                )

            # ログインユーザーは problem_id 必須
            if is_authenticated:
                if answer.get("problem_id") is None:
                    raise ValidationError(
                        message=f"answers[{idx}]: problem_id は必須です"
                    )
            # ゲストは order_index 必須
            else:
                if answer.get("order_index") is None:
                    raise ValidationError(
                        message=f"answers[{idx}]: order_index は必須です"
                    )

            key_value = answer.get(key_field)
            if key_value in seen_keys:
                raise ValidationError(
                    message=f"answers[{idx}]: {key_field} が重複しています"
                )
            seen_keys.add(key_value)

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
        # ProblemGroup を取得
        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        # 所有者チェック
        if problem_group.created_by_user != request.user:
            raise PermissionDeniedError(
                message="この問題グループにはアクセスできません"
            )

        # 問題グループ内の全問題を取得
        problems = list(
            Problem.objects.filter(problem_group=problem_group).order_by("order_index")
        )

        # problem_id → Problem のマッピング
        problem_map = {p.problem_id: p for p in problems}

        # answers の problem_id が全て存在するかチェック
        for answer in answers:
            if answer["problem_id"] not in problem_map:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"問題ID {answer['problem_id']} が見つかりません",
                )

        # 問題と回答のペアリストを構築
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

        # 一括採点実行
        try:
            grader = AnswerGrader()
            grading_results = grader.grade_batch(problems_with_answers)
        except AnswerGraderError as e:
            raise GradingError(message=str(e))

        # order_index → 採点結果のマッピング
        result_map = {r["order_index"]: r for r in grading_results}

        # 回答と採点結果を保存し、レスポンスを構築
        results = []
        with transaction.atomic():
            for item in problems_with_answers:
                problem = problem_map[item["problem_id"]]
                grading_result = result_map[item["order_index"]]

                # Answer を保存
                answer_record = Answer.objects.create(
                    problem=problem,
                    user=request.user,
                    answer_body=item["answer_body"],
                    grade=grading_result["grade"],
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
                        "solution": {
                            "version": 1,
                            "solution_body": grading_result["model_answer"],
                            "explanation": grading_result["explanation"],
                        },
                        "answer_id": answer_record.answer_id,
                    }
                )

        # order_index でソート
        results.sort(key=lambda x: x["problem_ref"]["order_index"])

        return Response(
            {
                "data": {"results": results},
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
        # セッションからゲスト問題データを取得
        guest_problem_data = request.session.get("guest_problem_data")
        if not guest_problem_data:
            raise GuestSessionNotFoundError(
                message="ゲストセッションが見つかりません。先に問題を生成してください。"
            )

        # ゲストトークンの一致確認
        session_token = guest_problem_data.get("guest_token")
        if session_token != guest_token:
            raise GuestTokenMismatchError(message="ゲストトークンが一致しません")

        # 問題データを取得
        problems = guest_problem_data.get("problems", [])
        problem_map = {p["order_index"]: p for p in problems}

        # answers の order_index が全て存在するかチェック
        for answer in answers:
            if answer["order_index"] not in problem_map:
                raise NotFoundError(
                    error_code=ErrorCode.PROBLEM_NOT_FOUND,
                    message=f"order_index {answer['order_index']} の問題が見つかりません",
                )

        # 問題と回答のペアリストを構築
        problems_with_answers = []
        for answer in answers:
            problem = problem_map[answer["order_index"]]
            problems_with_answers.append(
                {
                    "order_index": problem["order_index"],
                    "problem_type": problem["problem_type"],
                    "problem_body": problem["problem_body"],
                    "answer_body": answer["answer_body"],
                }
            )

        # 一括採点実行
        try:
            grader = AnswerGrader()
            grading_results = grader.grade_batch(problems_with_answers)
        except AnswerGraderError as e:
            raise GradingError(message=str(e))

        # order_index → 採点結果のマッピング
        result_map = {r["order_index"]: r for r in grading_results}

        # レスポンスを構築
        results = []
        for item in problems_with_answers:
            grading_result = result_map[item["order_index"]]

            results.append(
                {
                    "problem_ref": {
                        "order_index": item["order_index"],
                    },
                    "problem_type": item["problem_type"],
                    "grade": grading_result["grade"],
                    "grade_display": self.GRADE_DISPLAY_MAP.get(
                        grading_result["grade"], "×"
                    ),
                    "solution": {
                        "version": 1,
                        "solution_body": grading_result["model_answer"],
                        "explanation": grading_result["explanation"],
                    },
                }
            )

        # order_index でソート
        results.sort(key=lambda x: x["problem_ref"]["order_index"])

        # 採点成功後、guest_completed=True を設定
        request.session["guest_completed"] = True
        request.session.modified = True

        return Response(
            {
                "data": {"results": results},
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
