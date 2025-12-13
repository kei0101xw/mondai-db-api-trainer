"""認証関連のAPIビュー."""

from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from common.responses import success_response


@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request: Request):
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
