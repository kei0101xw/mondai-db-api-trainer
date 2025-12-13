"""エラーコード定義

アプリケーション全体で使用するエラーコードを定義します。
フロントエンドでエラーハンドリングを行う際に、このコードを参照します。
"""

from enum import Enum


class ErrorCode(str, Enum):
    """アプリケーション共通エラーコード."""

    # ========================================
    # 汎用エラー (1xxx)
    # ========================================
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # ========================================
    # 認証・認可エラー (2xxx)
    # ========================================
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # ========================================
    # リソースエラー (3xxx)
    # ========================================
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PROBLEM_GROUP_NOT_FOUND = "PROBLEM_GROUP_NOT_FOUND"
    PROBLEM_NOT_FOUND = "PROBLEM_NOT_FOUND"
    ANSWER_NOT_FOUND = "ANSWER_NOT_FOUND"

    # ========================================
    # ゲスト制限エラー (4xxx)
    # ========================================
    GUEST_LIMIT_REACHED = "GUEST_LIMIT_REACHED"
    GUEST_ALREADY_GENERATED = "GUEST_ALREADY_GENERATED"
    GUEST_TOKEN_INVALID = "GUEST_TOKEN_INVALID"
    GUEST_TOKEN_REQUIRED = "GUEST_TOKEN_REQUIRED"

    # ========================================
    # ビジネスロジックエラー (5xxx)
    # ========================================
    INVALID_DIFFICULTY = "INVALID_DIFFICULTY"
    INVALID_APP_SCALE = "INVALID_APP_SCALE"
    INVALID_MODE = "INVALID_MODE"
    INVALID_PROBLEM_TYPE = "INVALID_PROBLEM_TYPE"
    INVALID_GRADE = "INVALID_GRADE"
    AI_GENERATION_FAILED = "AI_GENERATION_FAILED"
    AI_GRADING_FAILED = "AI_GRADING_FAILED"

    # ========================================
    # CSRF/セキュリティエラー (9xxx)
    # ========================================
    CSRF_TOKEN_MISSING = "CSRF_TOKEN_MISSING"
    CSRF_TOKEN_INVALID = "CSRF_TOKEN_INVALID"


# エラーコードに対応するデフォルトメッセージ
ERROR_MESSAGES = {
    # 汎用エラー
    ErrorCode.INTERNAL_SERVER_ERROR: "内部サーバーエラーが発生しました",
    ErrorCode.INVALID_REQUEST: "不正なリクエストです",
    ErrorCode.VALIDATION_ERROR: "入力内容に誤りがあります",
    # 認証・認可エラー
    ErrorCode.UNAUTHORIZED: "認証が必要です",
    ErrorCode.FORBIDDEN: "アクセス権限がありません",
    ErrorCode.INVALID_CREDENTIALS: "メールアドレスまたはパスワードが正しくありません",
    ErrorCode.EMAIL_ALREADY_EXISTS: "このメールアドレスは既に登録されています",
    ErrorCode.SESSION_EXPIRED: "セッションの有効期限が切れました",
    # リソースエラー
    ErrorCode.NOT_FOUND: "リソースが見つかりません",
    ErrorCode.RESOURCE_NOT_FOUND: "指定されたリソースが見つかりません",
    ErrorCode.PROBLEM_GROUP_NOT_FOUND: "問題グループが見つかりません",
    ErrorCode.PROBLEM_NOT_FOUND: "問題が見つかりません",
    ErrorCode.ANSWER_NOT_FOUND: "回答が見つかりません",
    # ゲスト制限エラー
    ErrorCode.GUEST_LIMIT_REACHED: "ゲストユーザーの利用上限に達しました。続けるにはログインしてください",
    ErrorCode.GUEST_ALREADY_GENERATED: "ゲストユーザーは1問のみ生成できます",
    ErrorCode.GUEST_TOKEN_INVALID: "無効なゲストトークンです",
    ErrorCode.GUEST_TOKEN_REQUIRED: "ゲストトークンが必要です",
    # ビジネスロジックエラー
    ErrorCode.INVALID_DIFFICULTY: "無効な難易度が指定されました",
    ErrorCode.INVALID_APP_SCALE: "無効なアプリ規模が指定されました",
    ErrorCode.INVALID_MODE: "無効なモードが指定されました",
    ErrorCode.INVALID_PROBLEM_TYPE: "無効な問題種別が指定されました",
    ErrorCode.INVALID_GRADE: "無効な評価が指定されました",
    ErrorCode.AI_GENERATION_FAILED: "問題生成に失敗しました",
    ErrorCode.AI_GRADING_FAILED: "採点処理に失敗しました",
    # CSRF/セキュリティエラー
    ErrorCode.CSRF_TOKEN_MISSING: "CSRFトークンが見つかりません",
    ErrorCode.CSRF_TOKEN_INVALID: "CSRFトークンが無効です",
}


def get_error_message(code: ErrorCode) -> str:
    """エラーコードに対応するデフォルトメッセージを取得する.

    Args:
        code: エラーコード

    Returns:
        str: デフォルトエラーメッセージ
    """
    return ERROR_MESSAGES.get(code, "エラーが発生しました")
