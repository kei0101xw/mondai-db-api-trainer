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
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiClientError(
                "GEMINI_API_KEY が設定されていません。環境変数に設定してください。"
            )

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.client = genai.Client(api_key=self.api_key)

    def generate_content(
        self,
        prompt: str,
        *,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """
        テキストを生成する

        Args:
            prompt: 生成プロンプト
            temperature: 生成のランダム性（0.0〜2.0）
            max_output_tokens: 最大トークン数
            response_format: レスポンスフォーマット（例: "application/json"）

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

            config = types.GenerateContentConfig(**config_params)

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            if not response.text:
                raise GeminiClientError("生成されたテキストが空です")

            return response.text

        except Exception as e:
            raise GeminiClientError(f"Gemini API の呼び出しに失敗しました: {e}") from e

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        JSON形式でテキストを生成する

        Args:
            prompt: 生成プロンプト
            temperature: 生成のランダム性（0.0〜2.0）
            max_output_tokens: 最大トークン数

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
        )
