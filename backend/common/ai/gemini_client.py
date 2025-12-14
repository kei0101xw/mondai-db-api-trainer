import os
from typing import Any, Optional
from google import genai
from google.genai import types


class GeminiClientError(Exception):
    """Gemini API関連のエラー"""

    pass


class GeminiClient:
    """
    Gemini API のクライアントクラス

    環境変数 GEMINI_API_KEY からAPIキーを読み込み、
    Gemini API へのリクエストを行う。

    タイムアウトはhttp_optionsを通じてリクエストレベルで適用されるため、
    タイムアウト後に不要なバックグラウンド処理が残ることはありません。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        default_timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiClientError(
                "GEMINI_API_KEY が設定されていません。環境変数に設定してください。"
            )

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.default_timeout = default_timeout
        # デフォルトのHTTPオプションでクライアントを作成
        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=default_timeout * 1000),
        )

    def generate_content(
        self,
        prompt: str,
        *,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        テキストを生成する

        Args:
            prompt: 生成プロンプト
            temperature: 生成のランダム性（0.0〜2.0）
            max_output_tokens: 最大トークン数
            response_format: レスポンスフォーマット（例: "application/json"）
            timeout: タイムアウト時間（秒）。Noneの場合はクライアントのデフォルト値を使用

        Returns:
            生成されたテキスト

        Raises:
            GeminiClientError: API呼び出しに失敗した場合
        """
        try:
            config_params: dict[str, Any] = {
                "temperature": temperature,
            }

            if max_output_tokens is not None:
                config_params["max_output_tokens"] = max_output_tokens

            if response_format is not None:
                config_params["response_mime_type"] = response_format

            # タイムアウトがデフォルト値と異なる場合はhttp_optionsを設定
            if timeout is not None and timeout != self.default_timeout:
                config_params["http_options"] = types.HttpOptions(
                    timeout=timeout * 1000
                )

            config = types.GenerateContentConfig(**config_params)

            # API呼び出し（タイムアウトはhttp_optionsで制御）
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            if not response.text:
                raise GeminiClientError("生成されたテキストが空です")

            return response.text

        except GeminiClientError:
            # 既にGeminiClientErrorの場合はそのまま再送出
            raise
        except Exception as e:
            # タイムアウトエラーの場合は分かりやすいメッセージに変換
            error_message = str(e).lower()
            if "timeout" in error_message or "timed out" in error_message:
                effective_timeout = (
                    timeout if timeout is not None else self.default_timeout
                )
                raise GeminiClientError(
                    f"Gemini API の呼び出しがタイムアウトしました（{effective_timeout}秒）"
                ) from e
            raise GeminiClientError(f"Gemini API の呼び出しに失敗しました: {e}") from e

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        timeout: int = 60,
    ) -> str:
        """
        JSON形式でテキストを生成する

        Args:
            prompt: 生成プロンプト
            temperature: 生成のランダム性（0.0〜2.0）
            max_output_tokens: 最大トークン数
            timeout: タイムアウト時間（秒）デフォルト60秒

        Returns:
            JSON形式の文字列

        Raises:
            GeminiClientError: API呼び出しに失敗した場合
        """
        return self.generate_content(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_format="application/json",
            timeout=timeout,
        )

    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        pass
