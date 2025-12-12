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
        generator = ProblemGenerator()
        try:
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
