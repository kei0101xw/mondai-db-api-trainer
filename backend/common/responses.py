"""統一レスポンス形式のユーティリティ.

統一APIレスポンス形式を生成するヘルパー関数を提供します:
- 成功時: {"data": <payload>, "error": null}
- 失敗時: {"data": null, "error": {"code": "<STRING>", "message": "<STRING>", "details": <ANY|null>}}
"""

from typing import Any

from rest_framework.response import Response


def success_response(data: Any, status: int = 200) -> Response:
    """成功レスポンスを生成する.

    Args:
        data: "data"フィールドに格納するペイロード
        status: HTTPステータスコード（デフォルト: 200）

    Returns:
        Response: 統一成功形式のDRF Response
    """
    return Response({"data": data, "error": None}, status=status)


def error_response(
    code: str, message: str, details: Any = None, status: int = 400
) -> Response:
    """エラーレスポンスを生成する.

    Args:
        code: エラーコード文字列（例: "VALIDATION_ERROR"）
        message: 人間が読めるエラーメッセージ
        details: 追加のエラー詳細情報（任意）
        status: HTTPステータスコード（デフォルト: 400）

    Returns:
        Response: 統一エラー形式のDRF Response
    """
    return Response(
        {"data": None, "error": {"code": code, "message": message, "details": details}},
        status=status,
    )
