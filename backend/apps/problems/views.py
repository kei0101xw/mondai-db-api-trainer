"""
問題生成API エンドポイント
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import ProblemGenerator, ProblemGeneratorError


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
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "INVALID_DIFFICULTY",
                        "message": "difficulty は easy, medium, hard のいずれかを指定してください",
                        "details": None,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not app_scale or app_scale not in ["small", "medium", "large"]:
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "INVALID_APP_SCALE",
                        "message": "app_scale は small, medium, large のいずれかを指定してください",
                        "details": None,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not mode or mode not in ["db_only", "api_only", "both"]:
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "INVALID_MODE",
                        "message": "mode は db_only, api_only, both のいずれかを指定してください",
                        "details": None,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ゲスト制限チェック
        if not request.user.is_authenticated:
            # ゲストが既に採点完了している場合
            if request.session.get("guest_completed"):
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "GUEST_LIMIT_REACHED",
                            "message": "ゲストユーザーは1問のみ解くことができます。続けるには会員登録してください。",
                            "details": None,
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ゲストが既に問題を生成している場合
            if request.session.get("guest_problem_token"):
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "GUEST_ALREADY_GENERATED",
                            "message": "ゲストユーザーは既に問題を生成しています。先に回答を提出してください。",
                            "details": None,
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
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
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "GENERATION_ERROR",
                        "message": str(e),
                        "details": None,
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GradeAnswerView(APIView):
    """
    POST /api/v1/grade

    採点エンドポイント
    - ログインユーザー: problem_idで問題を特定し、DBに保存して採点結果を返す
    - ゲストユーザー: order_index + guest_tokenで問題を特定し、採点結果のみ返す
    """

    def post(self, request):
        """
        回答を採点する

        Request Body:
            {
                "problem_id": 123,           // ログインユーザーの場合必須
                "order_index": 1,            // ゲストの場合必須
                "guest_token": "...",        // ゲストの場合必須
                "answer_body": "回答本文"
            }

        Response (200):
            {
                "data": {
                    "grade": 2,
                    "grade_display": "○",
                    "model_answer": "模範解答",
                    "explanation": "解説",
                    "answer_id": 456  // ログインユーザーのみ
                },
                "error": null
            }
        """
        # リクエストパラメータ取得
        problem_id = request.data.get("problem_id")
        order_index = request.data.get("order_index")
        guest_token = request.data.get("guest_token")
        answer_body = request.data.get("answer_body")

        # answer_body バリデーション
        if (
            not answer_body
            or not isinstance(answer_body, str)
            or not answer_body.strip()
        ):
            return Response(
                {
                    "data": None,
                    "error": {
                        "code": "MISSING_ANSWER_BODY",
                        "message": "answer_body は必須です",
                        "details": None,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # XOR入力ルールチェック
        is_authenticated = request.user.is_authenticated
        has_problem_id = problem_id is not None
        has_guest_info = order_index is not None and guest_token is not None

        # ログインユーザーの場合
        if is_authenticated:
            if not has_problem_id:
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "MISSING_PROBLEM_ID",
                            "message": "ログインユーザーは problem_id が必須です",
                            "details": None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if has_guest_info:
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "INVALID_INPUT_COMBINATION",
                            "message": "ログインユーザーは order_index と guest_token を指定できません",
                            "details": None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ゲストユーザーの場合
        else:
            if has_problem_id:
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "INVALID_INPUT_COMBINATION",
                            "message": "ゲストユーザーは problem_id を指定できません",
                            "details": None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not has_guest_info:
                return Response(
                    {
                        "data": None,
                        "error": {
                            "code": "MISSING_GUEST_INFO",
                            "message": "ゲストユーザーは order_index と guest_token が必須です",
                            "details": None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # TODO: ログインユーザー向け処理
        # TODO: ゲストユーザー向け処理

        return Response(
            {
                "data": None,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "実装中",
                    "details": None,
                },
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
