"""認証・ユーザーモデル."""

from typing import Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager):
    """Custom Userモデル用のマネージャー."""

    def create_user(self, email: str, name: str, password: Optional[str] = None):
        """通常のユーザーを作成する.

        Args:
            email: メールアドレス
            name: ユーザー名
            password: パスワード

        Returns:
            User: 作成されたユーザー

        Raises:
            ValueError: emailまたはnameが指定されていない場合
        """
        if not email:
            raise ValueError("メールアドレスは必須です")
        if not name:
            raise ValueError("ユーザー名は必須です")

        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, name: str, password: Optional[str] = None):
        """スーパーユーザーを作成する.

        Args:
            email: メールアドレス
            name: ユーザー名
            password: パスワード

        Returns:
            User: 作成されたスーパーユーザー
        """
        user = self.create_user(email=email, name=name, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """カスタムユーザーモデル.

    AGENTS.md セクション6のDB設計に準拠したUserモデル。
    メールアドレスをユーザー名として使用し、nameフィールドを持つ。
    """

    user_id = models.BigAutoField(primary_key=True, verbose_name="ユーザーID")
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="メールアドレス",
        help_text="ログインに使用するメールアドレス",
    )
    name = models.CharField(max_length=255, verbose_name="ユーザー名")
    icon_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="アイコンURL",
        help_text="プロフィール画像のURL",
    )
    is_active = models.BooleanField(default=True, verbose_name="有効フラグ")
    is_staff = models.BooleanField(
        default=False,
        verbose_name="スタッフフラグ",
        help_text="管理画面へのアクセス権限",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self) -> str:
        """文字列表現を返す."""
        return f"{self.name} ({self.email})"
