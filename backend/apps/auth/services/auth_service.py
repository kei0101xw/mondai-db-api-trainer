"""認証関連のビジネスロジック."""

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction

from apps.auth.models import User
from common.exceptions import EmailAlreadyExistsError, InvalidCredentialsError


@transaction.atomic
def register_user(email: str, password: str, name: str) -> User:
    """ユーザーを新規登録する.

    トランザクション内でユーザーを作成します。
    メールアドレスの重複チェックはSerializer層で実施済みですが、
    同時登録などでDB制約に当たる場合に備えてIntegrityErrorも処理します。

    Args:
        email: メールアドレス（正規化済み）
        password: パスワード（平文）
        name: ユーザー名

    Returns:
        User: 作成されたユーザーオブジェクト

    Raises:
        EmailAlreadyExistsError: メールアドレスが既に登録されている場合
    """
    try:
        # UserManagerのcreate_userメソッドを使用
        # パスワードは自動的にハッシュ化されます
        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
        )
        return user
    except IntegrityError as e:
        # DB UNIQUE制約違反（同時登録などで発生）
        # emailフィールドのUNIQUE制約違反の場合
        if "email" in str(e).lower() or "unique" in str(e).lower():
            raise EmailAlreadyExistsError("このメールアドレスは既に登録されています")
        # その他のIntegrityError
        raise


def authenticate_user(email: str, password: str) -> User:
    """ユーザー認証を行う.

    Django標準のauthenticate()を使用して認証します。
    認証に失敗した場合は、セキュリティのため詳細を明かさない
    一般的なエラーメッセージを返します。

    Args:
        email: メールアドレス（正規化済み）
        password: パスワード（平文）

    Returns:
        User: 認証されたユーザーオブジェクト

    Raises:
        InvalidCredentialsError: 認証に失敗した場合
            - メールアドレスが存在しない
            - パスワードが一致しない
            - ユーザーが無効化されている（is_active=False）
    """
    # Django標準のauthenticate()を使用
    # USERNAME_FIELD（email）とパスワードで認証
    user = authenticate(username=email, password=password)

    if user is None:
        # 認証失敗
        # セキュリティのため、メールアドレスの存在有無を判別できないメッセージにする
        raise InvalidCredentialsError(
            message="メールアドレスまたはパスワードが正しくありません",
        )

    # is_active=Falseのユーザーはauthenticate()がNoneを返すため
    # ここに到達した時点でユーザーは有効

    return user
