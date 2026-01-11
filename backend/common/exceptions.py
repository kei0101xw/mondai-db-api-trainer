"""カスタム例外クラス定義

アプリケーション全体で使用する例外クラスを定義します。
各例外はエラーコードと紐付き、グローバル例外ハンドラーで統一レスポンスに変換されます。
"""

from typing import Any, Optional

from rest_framework import status

from .error_codes import ErrorCode, get_error_message


class AppException(Exception):
    """アプリケーション共通の基底例外クラス.

    すべてのカスタム例外はこのクラスを継承します。
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Any = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        """例外を初期化する.

        Args:
            error_code: エラーコード
            message: エラーメッセージ（省略時はデフォルトメッセージを使用）
            details: 追加のエラー詳細情報
            status_code: HTTPステータスコード
        """
        self.error_code = error_code
        self.message = message or get_error_message(error_code)
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppException):
    """バリデーションエラー."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """バリデーションエラーを初期化する.

        Args:
            message: エラーメッセージ
            details: バリデーションエラーの詳細（フィールド別エラー等）
        """
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UnauthorizedError(AppException):
    """認証エラー（未ログイン）."""

    def __init__(self, message: Optional[str] = None) -> None:
        """認証エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    """認可エラー（権限不足）."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """認可エラーを初期化する.

        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(AppException):
    """リソース未検出エラー."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.NOT_FOUND,
        message: Optional[str] = None,
    ) -> None:
        """リソース未検出エラーを初期化する.

        Args:
            error_code: エラーコード（デフォルト: NOT_FOUND）
            message: エラーメッセージ
        """
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidCredentialsError(AppException):
    """認証情報エラー（メール・パスワード不一致等）."""

    def __init__(self, message: Optional[str] = None) -> None:
        """認証情報エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class EmailAlreadyExistsError(AppException):
    """メールアドレス重複エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """メールアドレス重複エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class GuestLimitReachedError(AppException):
    """ゲストユーザー利用制限エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """ゲスト利用制限エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.GUEST_LIMIT_REACHED,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class GuestAlreadyGeneratedError(AppException):
    """ゲストユーザー問題生成済みエラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """ゲスト問題生成済みエラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.GUEST_ALREADY_GENERATED,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class GuestTokenInvalidError(AppException):
    """ゲストトークン無効エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """ゲストトークン無効エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.GUEST_TOKEN_INVALID,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class AIGenerationFailedError(AppException):
    """AI問題生成失敗エラー."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """AI問題生成失敗エラーを初期化する.

        Args:
            message: エラーメッセージ
            details: 失敗詳細情報
        """
        super().__init__(
            error_code=ErrorCode.AI_GENERATION_FAILED,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AIGradingFailedError(AppException):
    """AI採点失敗エラー."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """AI採点失敗エラーを初期化する.

        Args:
            message: エラーメッセージ
            details: 失敗詳細情報
        """
        super().__init__(
            error_code=ErrorCode.AI_GRADING_FAILED,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class PermissionDeniedError(AppException):
    """権限拒否エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """権限拒否エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.PERMISSION_DENIED,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ProblemInProgressError(AppException):
    """進行中の問題が存在するエラー (409 Conflict)."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """進行中コンフリクトを初期化する.

        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            error_code=ErrorCode.PROBLEM_IN_PROGRESS,
            message=message,
            details=details,
            status_code=status.HTTP_409_CONFLICT,
        )


class GuestSessionNotFoundError(AppException):
    """ゲストセッション未検出エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """ゲストセッション未検出エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.GUEST_SESSION_NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class GuestTokenMismatchError(AppException):
    """ゲストトークン不一致エラー."""

    def __init__(self, message: Optional[str] = None) -> None:
        """ゲストトークン不一致エラーを初期化する.

        Args:
            message: エラーメッセージ
        """
        super().__init__(
            error_code=ErrorCode.GUEST_TOKEN_MISMATCH,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class GenerationError(AppException):
    """問題生成エラー."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """問題生成エラーを初期化する.

        Args:
            message: エラーメッセージ
            details: エラー詳細情報
        """
        super().__init__(
            error_code=ErrorCode.GENERATION_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class GradingError(AppException):
    """採点エラー."""

    def __init__(self, message: Optional[str] = None, details: Any = None) -> None:
        """採点エラーを初期化する.

        Args:
            message: エラーメッセージ
            details: エラー詳細情報
        """
        super().__init__(
            error_code=ErrorCode.GRADING_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
