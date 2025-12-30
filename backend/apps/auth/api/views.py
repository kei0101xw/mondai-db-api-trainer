"""認証関連のAPIビュー."""

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.auth.api.serializers import (
    UserLoginSerializer,
    UserRegisterSerializer,
    UserSerializer,
)
from apps.auth.services import authenticate_user, register_user
from common.responses import success_response


@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request: Request) -> Response:
    """CSRFトークンを取得する.

    SPAからPOSTリクエストを送信する前に、このエンドポイントでCSRFトークンを取得します。
    トークンはCookieとレスポンスボディの両方で返されます。

    Args:
        request: DRFのRequestオブジェクト

    Returns:
        Response: CSRFトークンを含む統一レスポンス形式
    """
    # CSRFトークンを生成・取得（Cookieにセットされる）
    csrf_token = get_token(request)

    return success_response(
        data={"csrfToken": csrf_token},
        status=200,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user_view(request: Request) -> Response:
    """ユーザー新規登録.

    新しいユーザーを登録し、自動的にログインします。

    Args:
        request: DRFのRequestオブジェクト
            - email: メールアドレス
            - password: パスワード
            - name: ユーザー名

    Returns:
        Response: 登録されたユーザー情報を含む統一レスポンス形式

    Raises:
        ValidationError: バリデーションエラー（メールアドレス重複、パスワード要件など）
    """
    # バリデーション
    serializer = UserRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # ユーザー登録
    user = register_user(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        name=serializer.validated_data["name"],
    )

    # 自動ログイン（backend属性を明示的に指定）
    # register_user()で作成したユーザーはauthenticate()経由ではないため
    # backend属性がなく、login()でValueErrorが発生する
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # ゲスト関連のセッション情報をクリア
    # ゲストモードで問題を生成した後にログインした場合、ゲスト情報を引き継がない
    request.session.pop("guest_problem_token", None)
    request.session.pop("current_problem_group_id", None)
    request.session.pop("guest_completed", None)

    # レスポンス
    user_data = UserSerializer(user).data
    # 進行中の問題ID（新規登録後はNone）
    current_problem_group_id = request.session.get("current_problem_group_id")
    return success_response(
        data={"user": user_data, "current_problem_group_id": current_problem_group_id},
        status=201,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_user_view(request: Request) -> Response:
    """ユーザーログイン.

    メールアドレスとパスワードで認証し、セッションを開始します。

    Args:
        request: DRFのRequestオブジェクト
            - email: メールアドレス
            - password: パスワード

    Returns:
        Response: ログインしたユーザー情報を含む統一レスポンス形式

    Raises:
        InvalidCredentialsError: 認証失敗（メールアドレスまたはパスワードが正しくない）
    """
    # バリデーション
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # 認証
    user = authenticate_user(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )

    # ログイン（セッション開始）
    login(request, user)

    # ゲスト関連のセッション情報をクリア
    # ゲストモードで問題を生成した後にログインした場合、ゲスト情報を引き継がない
    request.session.pop("guest_problem_token", None)
    request.session.pop("current_problem_group_id", None)
    request.session.pop("guest_completed", None)

    # レスポンス
    user_data = UserSerializer(user).data
    # 進行中の問題ID（ログイン後はNone）
    current_problem_group_id = request.session.get("current_problem_group_id")
    return success_response(
        data={"user": user_data, "current_problem_group_id": current_problem_group_id},
        status=200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_user_view(request: Request) -> Response:
    """ユーザーログアウト.

    現在のセッションを終了します。

    Args:
        request: DRFのRequestオブジェクト

    Returns:
        Response: 成功メッセージを含む統一レスポンス形式
    """
    # ログアウト（セッション削除）
    logout(request)

    # レスポンス
    return success_response(data={"ok": True}, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user_view(request: Request) -> Response:
    """現在のログインユーザー情報を取得する.

    Args:
        request: DRFのRequestオブジェクト

    Returns:
        Response: ログイン中のユーザー情報を含む統一レスポンス形式
    """
    # request.userは認証済み（IsAuthenticatedで保証）
    user_data = UserSerializer(request.user).data

    # 進行中の問題ID（セッションから取得）
    current_problem_group_id = request.session.get("current_problem_group_id")

    # レスポンス
    return success_response(
        data={"user": user_data, "current_problem_group_id": current_problem_group_id},
        status=200,
    )
