"""バリデーションエラー整形ユーティリティ.

DRF（Django REST Framework）のバリデーションエラーを
統一レスポンス形式に変換する機能を提供します。
"""

from typing import Any


def format_validation_errors(errors: dict[str, Any]) -> dict[str, list[str]]:
    """DRFのバリデーションエラーを整形する.

    DRFのserializer.errorsは様々な形式のエラーを返すため、
    フロントエンドで扱いやすい形式に統一します。

    Args:
        errors: DRFのserializer.errorsオブジェクト

    Returns:
        dict[str, list[str]]: フィールド名をキー、エラーメッセージリストを値とする辞書

    例:
        入力: {"email": [ErrorDetail("This field is required.", code="required")]}
        出力: {"email": ["This field is required."]}

        入力: {"non_field_errors": ["Invalid data."]}
        出力: {"non_field_errors": ["Invalid data."]}
    """
    formatted_errors: dict[str, list[str]] = {}

    for field, error_list in errors.items():
        # ErrorDetailオブジェクトを文字列に変換
        if isinstance(error_list, list):
            formatted_errors[field] = [str(error) for error in error_list]
        elif isinstance(error_list, dict):
            # ネストされたエラー（例: リスト内のオブジェクトのバリデーション）
            formatted_errors[field] = _flatten_nested_errors(error_list)
        else:
            formatted_errors[field] = [str(error_list)]

    return formatted_errors


def _flatten_nested_errors(nested_errors: dict[str, Any]) -> list[str]:
    """ネストされたバリデーションエラーをフラット化する.

    Args:
        nested_errors: ネストされたエラー辞書

    Returns:
        list[str]: フラット化されたエラーメッセージリスト
    """
    messages = []
    for key, value in nested_errors.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    messages.extend(_flatten_nested_errors(item))
                else:
                    messages.append(f"{key}: {str(item)}")
        elif isinstance(value, dict):
            messages.extend(_flatten_nested_errors(value))
        else:
            messages.append(f"{key}: {str(value)}")
    return messages


def get_first_validation_error(errors: dict[str, Any]) -> str:
    """バリデーションエラーから最初のエラーメッセージを取得する.

    複数のフィールドでエラーが発生した場合、最初のエラーメッセージのみを返します。
    これは、シンプルなエラー表示が必要な場合に使用します。

    Args:
        errors: DRFのserializer.errorsオブジェクト

    Returns:
        str: 最初のエラーメッセージ
    """
    formatted = format_validation_errors(errors)
    for field_errors in formatted.values():
        if field_errors:
            return field_errors[0]
    return "入力内容に誤りがあります"
