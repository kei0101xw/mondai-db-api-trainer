def build_problem_generation_prompt(difficulty: str, app_scale: str, mode: str) -> str:
    """
    問題生成用のプロンプトを構築する

    Args:
        difficulty: 難易度 (easy/medium/hard)
        app_scale: アプリ規模 (small/medium/large)
        mode: モード (db_only/api_only/both)

    Returns:
        Gemini API に投げるプロンプト文字列
    """

    # 難易度の説明
    difficulty_desc = {
        "easy": "初心者向け。基本的なテーブル設計やCRUD APIのみ。",
        "medium": "中級者向け。リレーション、インデックス、複雑なクエリを含む。",
        "hard": "上級者向け。パフォーマンス最適化、セキュリティ、スケーラビリティを考慮。",
    }

    # アプリ規模の説明
    scale_desc = {
        "small": "小規模（5テーブル以下、5エンドポイント以下）",
        "medium": "中規模（5〜10テーブル、10〜15エンドポイント）",
        "large": "大規模（10テーブル以上、15エンドポイント以上）",
    }

    # モードに応じた問題タイプ
    mode_instruction = {
        "db_only": """
# 問題タイプ
- DB設計問題のみを生成してください

# 期待する出力
"problems" 配列には1つの要素（problem_type: "db"）のみを含めてください。
""",
        "api_only": """
# 問題タイプ
- API設計問題のみを生成してください

# 期待する出力
"problems" 配列には1つの要素（problem_type: "api"）のみを含めてください。
""",
        "both": """
# 問題タイプ
- DB設計問題とAPI設計問題の両方を生成してください

# 期待する出力
"problems" 配列には2つの要素を含めてください：
1. DB設計問題（problem_type: "db", order_index: 1）
2. API設計問題（problem_type: "api", order_index: 2）
""",
    }

    prompt = f"""あなたはバックエンドエンジニア向けの問題作成専門家です。
以下の条件に基づいて、データベース設計・API設計の練習問題を生成してください。

# 条件
- 難易度: {difficulty} ({difficulty_desc.get(difficulty, "")})
- アプリ規模: {app_scale} ({scale_desc.get(app_scale, "")})
- モード: {mode}

{mode_instruction.get(mode, "")}

# アプリの題材例
- SNSアプリ（投稿、いいね、フォロー機能）
- ECサイト（商品、カート、注文機能）
- タスク管理アプリ（プロジェクト、タスク、担当者管理）
- ブログシステム（記事、カテゴリ、コメント機能）
- 予約システム（施設、予約枠、予約管理）

上記はあくまで例です。他の現実的なWebアプリの題材でも構いません。

# 出力形式（JSON）
必ず以下のJSON形式で出力してください。JSONのみを出力し、それ以外の説明文は含めないでください。

```json
{{
  "title": "題材のタイトル（例：SNSアプリ）",
  "description": "アプリの概要説明。どのような機能を持つアプリか詳しく記述。",
  "problems": [
    {{
      "problem_type": "db",
      "order_index": 1,
      "problem_body": "DB設計問題の本文。具体的な要件を記述。\\n\\n例：以下の要件を満たすデータベース設計を行ってください。\\n- ユーザー管理\\n- 投稿機能\\n- いいね機能\\n\\nSQLのCREATE TABLE文で回答してください。"
    }},
    {{
      "problem_type": "api",
      "order_index": 2,
      "problem_body": "API設計問題の本文。具体的なエンドポイント要件を記述。\\n\\n例：以下のAPIエンドポイントを設計し、擬似コードで実装してください。\\n- POST /posts - 投稿作成\\n- GET /posts - 投稿一覧取得\\n- POST /posts/:id/like - いいね"
    }}
  ]
}}
```

# 注意事項
- problem_body には具体的な要件を詳しく記述してください
- DB設計問題では、テーブル構造、カラム、制約、リレーションを明確に示してください
- API設計問題では、HTTPメソッド、URL、リクエスト/レスポンス形式を明確に示してください
- 難易度とアプリ規模に応じて、問題の複雑さを調整してください
- 必ずJSONのみを出力してください（```json マーカーも不要です）
"""

    return prompt
