"""認証関連のシリアライザー."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.auth.models import User
from common.error_codes import ErrorCode
from common.exceptions import ValidationError


class UserSerializer(serializers.ModelSerializer):
    """ユーザー情報のレスポンス用シリアライザー.

    パスワードなどの機密情報を除外し、クライアントに返すべき情報のみを含めます。
    """

    class Meta:
        model = User
        fields = ["user_id", "email", "name", "icon_url", "created_at"]
        read_only_fields = ["user_id", "created_at"]


class UserRegisterSerializer(serializers.Serializer):
    """ユーザー新規登録用シリアライザー.

    バリデーション:
    - メールアドレスの重複チェック
    - パスワード強度のチェック（Django標準バリデーター使用）
    """

    email = serializers.EmailField(
        max_length=255,
        required=True,
        help_text="ログインに使用するメールアドレス",
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="パスワード（8文字以上推奨）",
    )
    name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="ユーザー名",
    )

    def validate_email(self, value: str) -> str:
        """メールアドレスの重複をチェックする.

        Args:
            value: メールアドレス

        Returns:
            str: 正規化されたメールアドレス

        Raises:
            ValidationError: メールアドレスが既に登録されている場合
        """
        # メールアドレスを正規化（小文字化）
        normalized_email = value.lower()

        # 重複チェック
        if User.objects.filter(email=normalized_email).exists():
            raise ValidationError(
                error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                message="このメールアドレスは既に登録されています",
                details={"field": "email", "value": normalized_email},
            )

        return normalized_email

    def validate_password(self, value: str) -> str:
        """パスワードの強度をチェックする.

        Django標準のパスワードバリデーターを使用します。
        settings.pyで設定されたバリデーター（最小長、共通パスワード、数字のみ禁止など）を適用します。

        Args:
            value: パスワード

        Returns:
            str: バリデーション済みパスワード

        Raises:
            ValidationError: パスワードが要件を満たさない場合
        """
        try:
            # Django標準のパスワードバリデーション
            # settings.AUTH_PASSWORD_VALIDATORSで設定された検証を実行
            validate_password(value)
        except DjangoValidationError as e:
            # Djangoのバリデーションエラーを統一形式に変換
            raise ValidationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="パスワードが要件を満たしていません",
                details={"field": "password", "errors": list(e.messages)},
            )

        return value


class UserLoginSerializer(serializers.Serializer):
    """ユーザーログイン用シリアライザー.

    認証情報のバリデーションのみを行います。
    実際の認証処理はサービス層で実行されます。
    """

    email = serializers.EmailField(
        max_length=255,
        required=True,
        help_text="登録済みのメールアドレス",
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="パスワード",
    )

    def validate_email(self, value: str) -> str:
        """メールアドレスを正規化する.

        Args:
            value: メールアドレス

        Returns:
            str: 正規化されたメールアドレス
        """
        # メールアドレスを正規化（小文字化）
        return value.lower()
