"""グローバル例外ハンドラー.

DRFのデフォルト例外ハンドラーをカスタマイズし、
すべての例外を統一レスポンス形式に変換します。
"""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .error_codes import ErrorCode, get_error_message
from .exceptions import AppException
from .responses import error_response
from .validators import format_validation_errors, get_first_validation_error

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """カスタム例外ハンドラー.

    すべての例外を統一レスポンス形式に変換します。
    DRFのsettings.pyでEXCEPTION_HANDLERとして設定します。

    Args:
        exc: 発生した例外
        context: 例外が発生したコンテキスト（view, request等）

    Returns:
        Response: 統一エラー形式のレスポンス
    """
    # 1. カスタム例外（AppException）の処理
    if isinstance(exc, AppException):
        return error_response(
            code=exc.error_code.value,
            message=exc.message,
            details=exc.details,
            status=exc.status_code,
        )

    # 2. DRFの標準例外処理を実行
    response = drf_exception_handler(exc, context)

    # 3. DRFが処理できた例外を統一形式に変換
    if response is not None:
        return _handle_drf_exception(exc, response)

    # 4. Django標準例外の処理
    if isinstance(exc, Http404):
        return error_response(
            code=ErrorCode.NOT_FOUND.value,
            message=get_error_message(ErrorCode.NOT_FOUND),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return error_response(
            code=ErrorCode.FORBIDDEN.value,
            message=get_error_message(ErrorCode.FORBIDDEN),
            status=status.HTTP_403_FORBIDDEN,
        )

    # 5. 未処理の例外（500エラー）
    logger.exception("Unhandled exception occurred", exc_info=exc)
    return error_response(
        code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        message=get_error_message(ErrorCode.INTERNAL_SERVER_ERROR),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _handle_drf_exception(exc: Exception, response: Response) -> Response:
    """DRFの標準例外を統一形式に変換する.

    Args:
        exc: 発生した例外
        response: DRFが生成したレスポンス

    Returns:
        Response: 統一エラー形式のレスポンス
    """
    # バリデーションエラー
    if isinstance(exc, drf_exceptions.ValidationError):
        return error_response(
            code=ErrorCode.VALIDATION_ERROR.value,
            message=get_first_validation_error(response.data),
            details=format_validation_errors(response.data),
            status=response.status_code,
        )

    # 認証エラー（未ログイン）
    if isinstance(exc, drf_exceptions.NotAuthenticated):
        return error_response(
            code=ErrorCode.UNAUTHORIZED.value,
            message=get_error_message(ErrorCode.UNAUTHORIZED),
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 認可エラー（権限不足）
    if isinstance(exc, drf_exceptions.PermissionDenied):
        return error_response(
            code=ErrorCode.FORBIDDEN.value,
            message=str(exc) if str(exc) else get_error_message(ErrorCode.FORBIDDEN),
            status=status.HTTP_403_FORBIDDEN,
        )

    # リソース未検出
    if isinstance(exc, drf_exceptions.NotFound):
        return error_response(
            code=ErrorCode.NOT_FOUND.value,
            message=str(exc) if str(exc) else get_error_message(ErrorCode.NOT_FOUND),
            status=status.HTTP_404_NOT_FOUND,
        )

    # 不正なリクエスト
    if isinstance(exc, drf_exceptions.ParseError):
        return error_response(
            code=ErrorCode.INVALID_REQUEST.value,
            message=str(exc) if str(exc) else "リクエストの形式が正しくありません",
            status=status.HTTP_400_BAD_REQUEST,
        )

    # メソッド不許可
    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return error_response(
            code=ErrorCode.INVALID_REQUEST.value,
            message=f"メソッド {exc.detail} は許可されていません",
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # スロットリング
    if isinstance(exc, drf_exceptions.Throttled):
        return error_response(
            code=ErrorCode.INVALID_REQUEST.value,
            message="リクエストが多すぎます。しばらく待ってから再試行してください",
            details={"retry_after": exc.wait},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # その他のDRF例外
    return error_response(
        code=ErrorCode.INVALID_REQUEST.value,
        message=str(exc) if str(exc) else get_error_message(ErrorCode.INVALID_REQUEST),
        status=response.status_code,
    )
