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
    ProblemInProgressError,
    NotFoundError,
    GradingError,
)
from common.error_codes import ErrorCode

from .services import (
    ProblemGenerator,
    ProblemGeneratorError,
    AnswerGrader,
    AnswerGraderError,
)
from .models import ProblemGroup, Problem, Answer, Explanation, ModelAnswer
from .ranking_service import get_ranking, Period, ScoreType

# answer_body の長さ制限（約50KB）
MAX_ANSWER_BODY_LENGTH = 50000


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
        # バッチ認証チェック
        from django.conf import settings
        from .models import ProblemGroupAttempt

        batch_secret = request.headers.get("X-Batch-Secret")
        expected_secret = getattr(settings, "BATCH_SECRET_KEY", None)

        if not expected_secret or batch_secret != expected_secret:
            raise PermissionDeniedError(
                message="このAPIはバッチ専用です。直接アクセスできません。"
            )

        # リクエストパラメータ取得
        min_stock = request.data.get("min_stock", 5)

        # バリデーション
        if not isinstance(min_stock, int) or min_stock < 1:
            raise ValidationError(message="min_stock は1以上の整数を指定してください")

        difficulties = ["easy", "medium", "hard"]
        results = []
        total_generated = 0

        for difficulty in difficulties:
            # 在庫数をカウント: 全問題数 - 解答済み問題数
            total_count = ProblemGroup.objects.filter(difficulty=difficulty).count()

            # 少なくとも1人以上が解答した問題グループのIDを取得
            attempted_ids = (
                ProblemGroupAttempt.objects.filter(problem_group__difficulty=difficulty)
                .values_list("problem_group_id", flat=True)
                .distinct()
            )

            attempted_count = len(set(attempted_ids))
            stock_count = total_count - attempted_count

            # 補充が必要な場合
            generated_count = 0
            shortage = max(0, min_stock - stock_count)

            if shortage > 0:
                # 不足分を生成
                for _ in range(shortage):
                    try:
                        generator = ProblemGenerator()
                        problem_group, problems, _ = generator.generate(
                            difficulty=difficulty
                        )
                        generated_count += 1
                        total_generated += 1
                    except ProblemGeneratorError:
                        # エラーが発生しても次の問題生成は続行
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
                "data": {
                    "results": results,
                    "total_generated": total_generated,
                },
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

        # クエリパラメータ取得
        difficulty = request.query_params.get("difficulty")

        # バリデーション
        if not difficulty or difficulty not in ["easy", "medium", "hard"]:
            raise ValidationError(
                message="difficulty は easy, medium, hard のいずれかを指定してください"
            )

        # ログインユーザーの場合
        if request.user.is_authenticated:
            # 既に問題取得済みかチェック
            if request.session.get("current_problem_group_id"):
                raise ProblemInProgressError(
                    message="進行中の問題があります。先に完了してください"
                )

            # 未解答の問題を取得（最古のものから払い出し）
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

            # セッションに記録
            request.session["current_problem_group_id"] = problem_group.problem_group_id

            # 問題一覧を取得
            problems = list(problem_group.problems.all().order_by("order_index"))

            return Response(
                {
                    "data": {
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
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        # ゲストユーザーの場合
        else:
            # ゲスト制限チェック
            if request.session.get("guest_completed"):
                raise GuestLimitReachedError(
                    message="ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。"
                )

            if request.session.get("guest_problem_token"):
                raise GuestAlreadyGeneratedError(
                    message="ゲストユーザーは既に問題を取得済みです。先に回答を完了してください。"
                )

            # 最古の1題を払い出し
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

            # ゲストトークン発行
            guest_token = secrets.token_urlsafe(32)
            request.session["guest_problem_token"] = guest_token
            request.session["current_problem_group_id"] = problem_group.problem_group_id

            # 問題一覧を取得
            problems = list(problem_group.problems.all().order_by("order_index"))

            return Response(
                {
                    "data": {
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
        key_field = "problem_id"
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

            # problem_id 必須（ログイン/ゲスト共通）
            if answer.get("problem_id") is None:
                raise ValidationError(message=f"answers[{idx}]: problem_id は必須です")

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
        # 進行中セッションと題材IDが一致するか確認
        current_pg_id = request.session.get("current_problem_group_id")
        if current_pg_id != problem_group_id:
            raise PermissionDeniedError(
                message="この題材は現在のセッションで進行中ではありません"
            )

        # ProblemGroup を取得
        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        # 問題グループ内の全問題を取得
        problems = list(
            Problem.objects.filter(problem_group=problem_group).order_by("order_index")
        )

        # problem_id → Problem のマッピング
        problem_map = {p.problem_id: p for p in problems}

        # 各問題の最新バージョンの模範解答を取得（事前生成分を優先して返す）
        model_answers = ModelAnswer.objects.filter(problem__in=problems).order_by(
            "problem_id", "-version"
        )
        latest_model_answer_map = {}
        for ma in model_answers:
            if ma.problem_id not in latest_model_answer_map:
                latest_model_answer_map[ma.problem_id] = ma

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

                # Explanation を保存（回答のバージョンに合わせる）
                Explanation.objects.create(
                    answer=answer_record,
                    version=answer_record.version,
                    explanation_body=grading_result["explanation"],
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
        # セッションのゲストトークン確認
        session_token = request.session.get("guest_problem_token")
        if not session_token:
            raise GuestSessionNotFoundError(
                message="ゲストセッションが見つかりません。先に問題を生成してください。"
            )
        if session_token != guest_token:
            raise GuestTokenMismatchError(message="ゲストトークンが一致しません")

        # 現在の題材IDを取得してDBから問題を解決
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

        # 各問題の最新模範解答（事前生成分）を取得
        model_answers = ModelAnswer.objects.filter(problem__in=problems).order_by(
            "problem_id", "-version"
        )
        latest_model_answer_map = {}
        for ma in model_answers:
            if ma.problem_id not in latest_model_answer_map:
                latest_model_answer_map[ma.problem_id] = ma

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

        # レスポンスを構築
        results = []
        for item in problems_with_answers:
            grading_result = result_map[item["order_index"]]

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
                }
            )

        # order_index でソート
        results.sort(key=lambda x: x["problem_ref"]["order_index"])

        # 採点では guest_completed を変更しない（完了APIで設定）

        return Response(
            {
                "data": {"results": results},
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

        # 題材の存在確認
        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_GROUP_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        # ログインユーザーの場合
        if request.user.is_authenticated:
            # セッションの題材IDと一致するか検証（払い出した本人のみ許可）
            current_id = request.session.get("current_problem_group_id")
            if current_id != problem_group_id:
                raise PermissionDeniedError(
                    message="この題材は現在のセッションで進行中ではありません"
                )

            # upsert (get_or_create)
            ProblemGroupAttempt.objects.get_or_create(
                problem_group=problem_group,
                user=request.user,
            )

            # セッションクリア
            if "current_problem_group_id" in request.session:
                del request.session["current_problem_group_id"]
            request.session.modified = True

            return Response(
                {"data": {"ok": True}, "error": None}, status=status.HTTP_200_OK
            )

        # ゲストユーザーの場合
        guest_token = request.data.get("guest_token")
        if not guest_token:
            raise ValidationError(message="guest_token は必須です")

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

        # 完了フラグ設定とセッションクリア
        request.session["guest_completed"] = True
        if "guest_problem_token" in request.session:
            del request.session["guest_problem_token"]
        if "current_problem_group_id" in request.session:
            del request.session["current_problem_group_id"]
        request.session.modified = True

        return Response(
            {"data": {"ok": True}, "error": None}, status=status.HTTP_200_OK
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
        # 認証チェック
        if not request.user.is_authenticated:
            raise PermissionDeniedError(
                message="復習機能を利用するにはログインが必要です"
            )

        # クエリパラメータ取得
        difficulty = request.query_params.get("difficulty")

        # フィルタ構築
        filters = {}

        if difficulty:
            if difficulty not in ["easy", "medium", "hard"]:
                raise ValidationError(
                    message="difficulty は easy, medium, hard のいずれかを指定してください"
                )
            filters["difficulty"] = difficulty

        from .models import ProblemGroupAttempt

        # ユーザーが解いた/進行した題材IDを収集（attempt または回答があるもの）
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
                    "data": {
                        "items": [],
                        "next_cursor": None,
                    },
                    "error": None,
                },
                status=status.HTTP_200_OK,
            )

        # 題材一覧を取得（created_at 降順）
        problem_groups = ProblemGroup.objects.filter(
            problem_group_id__in=list(target_ids), **filters
        ).order_by("-created_at")

        # レスポンス構築
        items = []
        for pg in problem_groups:
            # 問題数と回答状況を取得
            problems = list(pg.problems.all().order_by("order_index"))
            total_problems = len(problems)

            # ユーザーの最新回答を取得
            latest_grades = []
            answered_count = 0
            for problem in problems:
                latest_answer = (
                    Answer.objects.filter(problem=problem, user=request.user)
                    .order_by("-created_at")
                    .first()
                )
                if latest_answer:
                    latest_grades.append(latest_answer.grade)
                    answered_count += 1
                else:
                    latest_grades.append(None)

            items.append(
                {
                    "problem_group_id": pg.problem_group_id,
                    "title": pg.title,
                    "description": pg.description,
                    "difficulty": pg.difficulty,
                    "created_at": pg.created_at.isoformat(),
                    "answer_summary": {
                        "total_problems": total_problems,
                        "answered_problems": answered_count,
                        "latest_grades": latest_grades,
                    },
                }
            )

        return Response(
            {
                "data": {
                    "items": items,
                    "next_cursor": None,  # TODO: ページネーション実装時
                },
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
        # 認証チェック
        if not request.user.is_authenticated:
            raise PermissionDeniedError(
                message="復習機能を利用するにはログインが必要です"
            )

        # 題材を取得
        try:
            problem_group = ProblemGroup.objects.get(problem_group_id=problem_group_id)
        except ProblemGroup.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題グループID {problem_group_id} が見つかりません",
            )

        # 再挑戦開始オプション: クエリに start=true がある場合、セッションに current_problem_group_id を設定
        # （ログインユーザーのみ。復習から同じ題材を再回答可能にするため）
        start_flag = request.query_params.get("start")
        if start_flag == "true" and request.user.is_authenticated:
            request.session["current_problem_group_id"] = problem_group.problem_group_id
            request.session.modified = True

        # 問題一覧を取得
        problems = list(problem_group.problems.all().order_by("order_index"))

        # 各問題に対するユーザーの回答を取得
        answers_by_problem = {}
        grade_display_map = {0: "×", 1: "△", 2: "○"}

        for problem in problems:
            user_answers = Answer.objects.filter(
                problem=problem, user=request.user
            ).order_by("-created_at")

            answers_by_problem[problem.problem_id] = [
                {
                    "answer_id": a.answer_id,
                    "answer_body": a.answer_body,
                    "grade": a.grade,
                    "grade_display": grade_display_map.get(a.grade, "×"),
                    "created_at": a.created_at.isoformat(),
                }
                for a in user_answers
            ]

        # レスポンス構築
        return Response(
            {
                "data": {
                    "problem_group": {
                        "problem_group_id": problem_group.problem_group_id,
                        "title": problem_group.title,
                        "description": problem_group.description,
                        "difficulty": problem_group.difficulty,
                        "created_at": problem_group.created_at.isoformat(),
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

    # 有効な期間の値
    VALID_PERIODS = {"daily", "weekly", "monthly", "all"}
    # 有効なスコアタイプの値
    VALID_SCORE_TYPES = {"problem_count", "correct_count", "grade_sum"}

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
        # クエリパラメータ取得
        period_str = request.query_params.get("period", "daily")
        score_type_str = request.query_params.get("score_type", "problem_count")
        limit_str = request.query_params.get("limit", "5")

        # バリデーション: period
        if period_str not in self.VALID_PERIODS:
            raise ValidationError(
                message=f"period は {', '.join(self.VALID_PERIODS)} のいずれかを指定してください"
            )

        # バリデーション: score_type
        if score_type_str not in self.VALID_SCORE_TYPES:
            raise ValidationError(
                message=f"score_type は {', '.join(self.VALID_SCORE_TYPES)} のいずれかを指定してください"
            )

        # バリデーション: limit
        try:
            limit = int(limit_str)
            if limit < 1 or limit > 100:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                message="limit は 1 から 100 の整数を指定してください"
            )

        # Enum に変換
        period = Period(period_str)
        score_type = ScoreType(score_type_str)

        # ランキング取得
        rankings = get_ranking(period=period, score_type=score_type, limit=limit)

        # レスポンス構築
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
                "data": {
                    "period": period_str,
                    "score_type": score_type_str,
                    "rankings": rankings_data,
                },
                "error": None,
            },
            status=status.HTTP_200_OK,
        )


class ModelAnswerView(APIView):
    """
    GET /api/v1/problems/{problem_id}/model-answers

    模範解答取得エンドポイント
    - 認証不要（誰でも閲覧可能）
    """

    def get(self, request, problem_id: int):
        """
        特定の小問に対する模範解答を取得する

        Response (200):
            {
                "data": {
                    "model_answers": [
                        {
                            "problem_id": 1,
                            "version": 1,
                            "model_answer": "CREATE TABLE ..."
                        }
                    ]
                },
                "error": null
            }
        """
        from .models import ModelAnswer

        # 問題の存在チェック
        try:
            problem = Problem.objects.get(problem_id=problem_id)
        except Problem.DoesNotExist:
            raise NotFoundError(
                error_code=ErrorCode.PROBLEM_NOT_FOUND,
                message=f"問題ID {problem_id} が見つかりません",
            )

        # 模範解答を取得（複数バージョン対応）
        model_answers = ModelAnswer.objects.filter(problem=problem).order_by("version")

        return Response(
            {
                "data": {
                    "model_answers": [
                        {
                            "problem_id": ma.problem.problem_id,
                            "version": ma.version,
                            "model_answer": ma.model_answer,
                        }
                        for ma in model_answers
                    ]
                },
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

        # 認証チェック
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
                "data": {
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
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
