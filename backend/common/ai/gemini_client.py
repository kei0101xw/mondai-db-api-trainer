import atexit
import os
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from google import genai
from google.genai import types


class GeminiClientError(Exception):
    """Gemini API関連のエラー"""

    pass


# モジュールレベルでThreadPoolExecutorを共有することで、
# インスタンスごとにスレッドプールを作成せず、リソースリークを防ぐ
_shared_executor: Optional[ThreadPoolExecutor] = None


def _get_shared_executor() -> ThreadPoolExecutor:
    """
    共有のThreadPoolExecutorを取得する

    初回呼び出し時にexecutorを作成し、以降は同じインスタンスを返す。
    アプリケーション終了時にatexitでクリーンアップされる。
    """
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")
        # アプリケーション終了時にshutdownを実行
        atexit.register(_shutdown_shared_executor)
    return _shared_executor


def _shutdown_shared_executor() -> None:
    """共有のThreadPoolExecutorをシャットダウンする"""
    global _shared_executor
    if _shared_executor is not None:
        _shared_executor.shutdown(wait=True)
        _shared_executor = None


class GeminiClient:
    """
    Gemini API のクライアントクラス

    環境変数 GEMINI_API_KEY からAPIキーを読み込み、
    Gemini API へのリクエストを行う。

    Note:
        ThreadPoolExecutorはモジュールレベルで共有され、
        アプリケーション終了時に自動的にクリーンアップされます。
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiClientError(
                "GEMINI_API_KEY が設定されていません。環境変数に設定してください。"
            )

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.client = genai.Client(api_key=self.api_key)
        # 共有のスレッドプールを使用
        self._executor = _get_shared_executor()

    def generate_content(
        self,
        prompt: str,
        *,
        temperature: float = 1.0,
        max_output_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        """
        テキストを生成する

        Args:
            prompt: 生成プロンプト
            temperature: 生成のランダム性（0.0〜2.0）
            max_output_tokens: 最大トークン数
            response_format: レスポンスフォーマット（例: "application/json"）
            timeout: タイムアウト時間（秒）デフォルト60秒

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

            # API呼び出しをタイムアウト付きで実行
            # ThreadPoolExecutorを使用して、タイムアウトを確実に適用する
            def _call_api():
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

            future = self._executor.submit(_call_api)
            try:
                response = future.result(timeout=timeout)
            except FutureTimeoutError:
                future.cancel()
                raise GeminiClientError(
                    f"Gemini API の呼び出しがタイムアウトしました（{timeout}秒）"
                )

            if not response.text:
                raise GeminiClientError("生成されたテキストが空です")

            return response.text

        except GeminiClientError:
            # 既にGeminiClientErrorの場合はそのまま再送出
            raise
        except Exception as e:
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
        """
        コンテキストマネージャーの終了処理

        Note:
            共有executorを使用しているため、ここでは何もしない。
            個別インスタンスでのシャットダウンは不要。
        """
        pass
