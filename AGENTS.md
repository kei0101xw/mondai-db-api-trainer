# AGENTS.md

## 1. プロジェクト概要

### プロダクト名

- **mondAI**

### コンセプト

- バックエンドエンジニア（特に経験が浅い人）向けの
  - **データベース設計**
  - **API 設計**
- に特化した「設計問題練習用 Web アプリ」です。
- SNS アプリなど、現実的な題材を元に
  - 問題を生成し
  - 回答を書き
  - AI で採点と解説を返す
    という流れを繰り返すことで、設計の引き出しを増やすことを目標とします。

### 想定ユーザー

- Web バックエンド初学者
- 就活の面接で「DB 設計・API 設計」の問題対策をしたいエンジニア学生
- 自分の設計力を定期的にチェックしたい初〜中級エンジニア

---

## 2. 審査観点とプロダクトのゴール

本プロジェクトは「技育ハッカソン」に出場するためのものです。
審査は **オーディエンス投票方式** で行われ、主に以下の観点が見られます。

### 2.1 審査基準（要約）

1. **サービスとしての価値**
   - 世の中の役に立つか
   - 面白い・触っていて楽しいか
2. **サービスの完成度**
   - 実装されている機能が一通り使えるか
   - UI / UX が直感的でストレスなく操作できるか
3. **技術的な挑戦**
   - 新しい / 難しい技術にチャレンジしているか
   - 設計や実装に工夫が見られるか

### 2.2 mondAI として目指す方向

- **価値**
  - 「DB・API 設計」という抽象的になりがちなテーマを、**具体的な問題演習**として体験できること
  - 面接対策としてもそのまま使えるような、現実に近い題材の問題を用意すること
- **完成度**
  - ゲストでもワンクリックで問題を解いて遊べる
  - ログインユーザーは自分の回答・スコアを蓄積できる（データとして）
- **技術的な挑戦**
  - 問題生成と採点・解説に AI を活用する
  - DB スキーマ・API 設計自体も「ちゃんとした設計」を目指す

---

## 3. 開発スタック・構成方針

### 3.1 技術スタック

- **バックエンド**
  - Python / Django
  - Django REST Framework（DRF）で JSON API を提供
  - パッケージ管理：`uv`
  - Lint・Format：`Ruff`
- **データベース**
  - **PostgreSQL 16**（開発・本番ともに Postgres 前提）
- **フロントエンド**
  - React
  - TypeScript
  - Lint：`ESLint`
  - Format：`Prettier`

### 3.2 リポジトリ構成（モノレポ）

- `backend/`
  - Django プロジェクト・アプリケーション
  - DRF を用いた API 実装（ドメイン分割）
- `frontend/`
  - React + TypeScript の SPA
  - バックエンドの REST API を叩くクライアント

### 3.3 ディレクトリ構成（推奨）

#### backend（ドメイン分割）

```txt
backend/
  manage.py
  pyproject.toml
  .env.example
  config/                       # Django project (settings/urls/asgi/wsgi)
    settings.py
    urls.py
    asgi.py
    wsgi.py
  apps/
    accounts/                   # 認証・プロフィール（追加機能含む）
      api/                      # DRF: serializers/views/urls
      services/                 # ユースケース/ドメインサービス
      models.py
      migrations/
    problems/                   # 問題生成・保存
      api/
      services/
      models.py
      migrations/
    answers/                    # 回答・採点・解説
      api/
      services/
      models.py
      migrations/
  common/                       # 共通（例外/ユーティリティ/共通型など）
```

#### frontend（FSD 軽量版：pages + features + entities + shared）

```txt
frontend/
  package.json
  eslint.config.js
  .env.example
  src/
    app/
      providers/                # QueryClientProvider / AuthProvider など
      router/                   # react-router 定義
      App.tsx                   # Provider合成
    pages/                      # URLに対応する画面
      home/
      login/
      generate-problem/
      solve-problem/
      result/
    features/                   # “ユーザー操作”単位（フォーム/送信など）
      auth/
        login-form/
        register-form/
      problem/
        generate-form/
      answer/
        answer-editor/
        submit-answer/
    entities/                   # “ドメイン”単位（型・API関数）
      user/
        api.ts
        types.ts
      problem/
        api.ts
        types.ts
      answer/
        api.ts
        types.ts
    shared/                     # 共通
      api/
        client.ts               # API通信の共通クライアント
      ui/
      lib/
      hooks/
      types/
      constants/
```

---

## 4. MVP（ハッカソンで必ず実装する範囲）

MVP の目標は、

> 「ユーザー（またはゲスト）が 1 問生成して解き、採点と解説を見られる」

という一連の流れを、ストレスなく体験できるようにすることです。

### 4.1 認証・ゲスト

#### ログインユーザー

- メールアドレス＋パスワードによる
  - ユーザー登録
  - ログイン
  - ログアウト
- ログインユーザーの「生成した問題」「回答」「採点結果」は **DB に永続保存**する。

#### ゲストモード

- 会員登録なしで、「すぐに問題を 1 問解いてみる」ことができる。
- **ゲストは 1 問だけ**（問題生成 → 回答 → 採点・解説まで）。1 問解いた後は登録/ログインを促し、これ以上は解けないようにする。
- ゲストユーザーの「問題」「回答」「採点結果」は **永続保存しない**（cookie/session 等の一時状態でのみ保持）。
- ゲストとログインユーザーの両方で、同じ UI の流れを辿れることが望ましい。

### 4.2 事前生成方式（バッチ処理）

**問題は事前にバッチで生成されており**、ユーザーは在庫から払い出しを受ける形で問題を取得する。

- 1 回の AI（Gemini）API リクエストで問題と模範解答をまとめて生成する（コスト・速度・整合性の観点から最適）。
- AI 応答は構造化された JSON 形式で、問題本文と模範解答を同時に含む。
- 問題生成時の模範解答の `version` は常に `1`（初回生成時は必ずバージョン 1 から開始）。
- バッチ：1 時間おきに難易度ごとの在庫（回答済みになっていない問題）をチェックし、5 問を下回る難易度は問題生成 API を叩いて問題＋模範解答を補充する。5 問の在庫判定には、`problem_group_attempts`を用いて集計し判定する。（problem_groups に登録されているもののうち、problem_group_attempts にない問題の数をカウントする）
- 在庫ポリシー：難易度ごとに「まだ誰も回答していない問題」を常時 5 問以上確保する。

### 4.3 問題取得

ユーザー（ログイン or ゲスト）は、以下を指定して問題を取得する：

- **難易度のみ**
  - `easy | medium | hard`

現状の出力は **常に DB ＋ API 混合（mode=both）**。将来的に問題タイプを切り替えられるようにする拡張余地は残す（UI/API で拡張可能な前提）。

取得される問題は、以下のような構造を持つ：

- アプリの概要説明（例：SNS アプリ、EC サイトなど）
- 設計問題パート
  - DB 設計問題（必要テーブル・カラム・制約などを SQL ライクに記述させる）
  - API 設計問題（擬似コードで API を実装させる）
- モードに応じて、DB / API どちらを含めるかが変わる。

問題は事前生成時に、各小問（problem）に対する**模範解答（model_answer）も同時に生成**されており、`model_answers` テーブルに保存されている。

**ログインユーザーの場合：**

- 在庫から未解答の問題を 1 つ払い出し、その `problem_group_id` を記録する。
- 一度解いた問題は二度と払い出されない（`problem_group_attempts` テーブルで管理）。

**ゲストユーザーの場合：**

- 在庫からランダムに問題を 1 つ払い出し、`guest_token` を発行してセッションに保持する。
- 問題自体は DB に永続化されているが、ゲストの回答・採点結果は永続保存しない。

**セッション管理（バックエンド）**

- **ログインユーザー**
  - 問題取得 API 成功時、セッションに `current_problem_group_id` を記録する。
  - フロント（ホームページ・問題解答ページ）では、セッションの値を参考に「すでに生成した問題を解答する」ボタン或いは「問題を生成」ボタンを表示分岐。
  - 「問題終了」操作を実行するまで、セッション値は保持される（ページ離脱しても復元可能）。
- **ゲスト**
  - `guest_token` がセッションに保存済みのため、それから現在の `problem_group_id` を判定して表示。

### 4.4 問題回答

問題に対して、ユーザーは以下のように回答する：

- 現状は DB ＋ API 混合（mode=both）を出題するため、DB 設計回答と API 設計回答の 2 入力欄を表示する。
- 将来的に問題タイプを切り替え可能にする場合は、UI を拡張し単一入力モード（db_only/api_only）も扱えるようにする。

**ログインユーザーの場合：**

- 回答は `Answer`（または同等のモデル）として DB に保存する。
- 後の復習や分析に使えるよう、問題との紐付けも保存しておく。

**ゲストユーザーの場合：**

- 回答は永続保存せず、その場の画面表示のためだけに持つ。

### 4.5 採点・解説

AI による自動採点と解説表示を行う。

- 採点は、**マルバツサンカク（〇 ×△）**で行う。
- 採点と同時に、ユーザーの回答内容に合わせた**解説テキスト**を生成して返す（`explanations` テーブルに保存）。
- 模範解答は、問題生成時に事前生成済みのため、別途取得 API で参照する。
- ログインユーザーの場合：
  - 採点結果・解説は `Answer` / `explanations` レコードに紐づけて保存しておく。
- ゲストユーザーの場合：
  - 採点結果・解説は永続保存せず、その問題画面でのみ表示する。
- ログインユーザーは採点結果を見た上で押す「問題終了」操作によって `problem_group_attempts` に `(problem_group_id, user_id)` を upsert し、再払い出しを防ぐ（採点 API では upsert しない）。
- ゲストは同じ「問題終了」操作で `guest_completed` をセッションに保存し、それ以降の取得・採点を禁止する。

---

## 5. 追加機能（MVP 外）

ここに記載する機能は、「時間があれば実装したいが MVP ではない」ものです。

### 5.1 優先度 High の追加機能

- **ユーザープロフィール**
  - 表示名・アイコン・自己紹介などを登録・編集できる画面
- **復習画面（マイ問題一覧）**
  - ログインユーザーが過去に解いた問題の一覧
  - 各問題ごとに「問題文」「自分の回答」「採点結果」「模範解答・解説」を確認できる。
  - 難易度や解いた日時でソート／簡易フィルタ（タグではなく難易度などで絞り込む）。
- **問題の再挑戦機能**
  - 過去の問題に対して、再度回答を送ることができる。
  - 再回答をどのように保存するか（複数回答履歴を持つか）は別途設計。
- **問題評価**
  - ユーザーが問題に対して評価（例：5 段階評価・Like ボタンなど）を付ける。
  - 評価は後のプロンプト改善や「みんなの問題」表示条件に利用する。

### 5.2 優先度 Medium の追加機能

- **みんなの問題**
  - 他のユーザーが生成し、かつ高評価した問題の一覧ページ。
  - 自分で生成した問題と同様に解答できる。
- **ステータス画面**
  - ユーザーごとの
    - 解いた問題数
    - 平均採点結果
    - 難易度ごとの傾向
      などを可視化する。
- **ランキング**
  - 総スコアや解答数などに基づく簡易ランキング。
  - ハッカソンの演出として、トップページなどから見える形が望ましい。
- **採点結果の手動修正・再採点**
  - AI 採点が明らかにおかしい場合に、ユーザーが手動で採点結果を修正できる。
  - 修正履歴を保存し、AI 採点とユーザー修正との差分を後で分析できるようにする。
- **模範解答の再生成 API**
  - 既存問題の模範解答のみを再生成する専用 API（例：`POST /api/v1/model-answers/regenerate`）。
  - プロンプト改善や品質向上のため、既存問題はそのままで模範解答だけを更新したい場合に使用。
  - 新バージョンとして `model_answers` テーブルに追加保存し、過去バージョンも履歴として保持。
  - 運用者ロールまたはバッチ専用トークンに限定して権限管理を行う想定。

### 5.3 優先度 Low の追加機能

- **ゲストから本登録への引き継ぎ**
  - ゲストで解いた問題・回答を、後からユーザー登録した際に引き継ぐ。
- **より細かいフィルタ・検索**
  - 難易度・作成日時などによる絞り込み。

---

## 6. DB 設計

### users

- user_id (PK)
- name
- email (UNIQUE)
- password_hash
- icon_url (NULL 可)
- created_at
- updated_at

### problem_groups（題材）

- problem_group_id (PK)
- title
- description
- difficulty（easy/medium/hard）
- created_at
- updated_at
- CHECK(difficulty IN ('easy','medium','hard'))

### problems（題材内の小問）

- problem_id (PK)
- problem_group_id (FK → problem_groups.problem_group_id)
- problem_body
- problem_type（db/api）
- order_index（題材内で何問目か）
- created_at
- updated_at
- UNIQUE(problem_group_id, order_index)
- CHECK(problem_type IN ('db','api'))

### model_answers（小問に対する模範解答）

- problem_id (PK, FK → problems.problem_id)
- version (PK)
- model_answer
- created_at
- updated_at

### explanations（小問に対する解説）

- answer_id (PK, FK → answers.answer_id)
- version (PK)
- explanation_body
- created_at
- updated_at

### answers（小問に対する回答）

- answer_id (PK)
- problem_id (FK → problems.problem_id)
- user_id (FK → users.user_id)
- version
- answer_body
- grade（0/1/2 = ×/△/○）
- created_at
- updated_at
- CHECK(grade IN (0,1,2))

### problems_groups_evaluation（題材への評価）

- user_id (PK, FK → users.user_id)
- problem_group_id (PK, FK → problem_groups.problem_group_id)
- evaluation（高評価・低評価）※enum 等で型を確定
- evaluation_reason（NULL 可）
- created_at
- updated_at
- CHECK(evaluation IN (低評価,高評価))

### favorite_problems_groups（お気に入り）

- user_id (PK, FK → users.user_id)
- problem_group_id (PK, FK → problem_groups.problem_group_id)
- created_at
- updated_at

### problem_group_attempts（ログインユーザーがある題材を採点完了したことを管理）

- problem_group_id (PK, FK → problem_groups.problem_group_id)
- user_id (PK, FK → users.user_id)
- created_at
- updated_at

### sessions

- session_key VARCHAR(40) PRIMARY KEY,
- session_data LONGTEXT, ※JSON 形式の暗号化データ
- expire_date DATETIME

- Django の標準（`django_session`）を使う前提
  ※自前テーブルは作らない
- ## カラムは以下の 3 つ
- **セッションデータの主要キー：**

  - `current_problem_group_id`（INT, NULL 可）：ログインユーザーが現在解いている問題の ID。問題取得 API 成功時に設定、問題完了 API 成功時に削除。
  - `guest_problem_token`（STRING, NULL 可）：ゲストユーザーに発行したトークン。問題取得 API 成功時に設定、問題完了 API 成功時に削除。
  - `guest_completed`（BOOLEAN）：ゲストが既に 1 問を完了したかを示すフラグ。問題完了 API 成功時に `True` に設定。

  - **ユーザー識別について：**
  - `django_session` テーブルは `(session_key, session_data, expire_date)` の 3 カラムのみを持つ
  - ログインユーザーの識別は Django の認証機構（`request.user.id`）で自動的に行われるため、セッションデータに user_id を保存する必要はない
  - ゲストユーザーは `guest_token` で識別される
  - セッションキーは Cookie（`sessionid`）を通じてブラウザとサーバーで同期される

---

## 7. API 設計（MVP）

### 7.1 共通仕様

- Base URL：`/api/v1`
- 形式：REST / JSON
- 認証：Django 標準のログイン（セッション Cookie）を利用
  - フロントは `fetch(..., { credentials: "include" })` 前提
- レスポンス形式（成功時）
  - `{ "data": <payload>, "error": null }`
- レスポンス形式（失敗時）
  - `{ "data": null, "error": { "code": "<STRING>", "message": "<STRING>", "details": <ANY|null> } }`
- ステータスコード目安
  - 200 OK / 201 Created
  - 400 Bad Request（バリデーション）
  - 401 Unauthorized（未ログイン）
  - 403 Forbidden（ゲスト制限など）
  - 404 Not Found
  - 500 Internal Server Error

---

### 7.2 認証（Django セッション）

> SPA から安全に POST を行うため、CSRF トークン取得用エンドポイントを用意する。

#### GET `/api/v1/auth/csrf`

- 用途：CSRF Cookie を発行・取得する
- 認証：不要
- Response（200）

```json
{
  "data": { "csrfToken": "..." },
  "error": null
}
```

#### POST `/api/v1/auth/register`

- 用途：ユーザー新規登録
- 認証：不要
- Request

```json
{
  "email": "user@example.com",
  "password": "password",
  "name": "mondai user"
}
```

- Response（201）

```json
{
  "data": {
    "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" }
  },
  "error": null
}
```

#### POST `/api/v1/auth/login`

- 用途：ログイン（セッション確立）
- 認証：不要
- Request

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

- Response（200）

```json
{
  "data": {
    "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" }
  },
  "error": null
}
```

#### POST `/api/v1/auth/logout`

- 用途：ログアウト（セッション破棄）
- 認証：必要
- Response（200）

```json
{
  "data": { "ok": true },
  "error": null
}
```

#### GET `/api/v1/auth/me`

- 用途：ログイン中ユーザー情報取得
- 認証：必要
- Response（200）

```json
{
  "data": {
    "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" }
  },
  "error": null
}
```

- 用途：ログアウト（セッション破棄）
- 認証：必要
- **振る舞い**：
  - Django の `logout()` を実行し、セッションデータを完全にクリアする
  - `current_problem_group_id`、`guest_problem_token`、`guest_completed` などのセッションデータも全て削除される
  - 新しい匿名セッション（`session_key`）が自動的に発行される
- Response（200）

```json
{
  "data": { "ok": true },
  "error": null
}
```

---

### 7.3 問題生成・在庫管理

#### POST `/api/v1/problem-groups/generate`

- 用途：題材（problem_group）と小問（problems）を AI で生成し、同時に各小問の模範解答（model_answers）も生成・補充する
- **アクセス制限**：バッチ専用 API。一般ユーザー（ログイン/ゲスト）は直接呼び出せない
- **認証方式**：
  - リクエストヘッダーに `X-Batch-Secret: <BATCH_SECRET_KEY>` を含める
  - `BATCH_SECRET_KEY` は環境変数（`.env`）から読み込む
  - ヘッダーが一致しない場合は `403 Forbidden` を返す
- **在庫管理機能**：
  - 難易度ごとの在庫をチェック（全問題数 - 解答済み問題数）
  - 在庫が 5 問未満の難易度に対して自動補充
  - 1 時間おきに外部 cron サービス（cron-job.org 等）から呼び出し
- 生成方式：1 回の Gemini API リクエストで問題と模範解答をまとめて生成し、構造化 JSON レスポンスを受け取る（コスト・レイテンシ・整合性の観点から最適）
- 在庫ポリシー：難易度ごとに「まだ誰にも回答していない問題」を常時 5 問以上確保する

- Request（形式 1: 複数難易度を一括処理・推奨）

```json
{
  "difficulties": ["easy", "medium", "hard"]
}
```

- Request（形式 2: 単一難易度のみ生成・従来形式）

```json
{
  "difficulty": "easy"
}
```

- Request（デフォルト・全難易度を自動処理）

```json
{}
```

- Response（200）

```json
{
  "data": {
    "results": [
      {
        "difficulty": "easy",
        "total_count": 10,
        "attempted_count": 5,
        "stock_count": 5,
        "shortage": 0,
        "generated_count": 0,
        "problem_group": {
          "problem_group_id": 123,
          "title": "SNSアプリ",
          "description": "...",
          "difficulty": "easy",
          "created_at": "2025-12-12T00:00:00Z"
        },
        "problems": [
          {
            "problem_id": 1,
            "problem_group_id": 123,
            "problem_type": "db",
            "order_index": 1,
            "problem_body": "..."
          }
        ],
        "model_answers": [
          {
            "problem_id": 1,
            "version": 1,
            "model_answer": "CREATE TABLE users (...); ..."
          }
        ]
      },
      {
        "difficulty": "medium",
        "total_count": 8,
        "attempted_count": 3,
        "stock_count": 5,
        "shortage": 0,
        "generated_count": 0
      },
      {
        "difficulty": "hard",
        "total_count": 6,
        "attempted_count": 1,
        "stock_count": 5,
        "shortage": 0,
        "generated_count": 0
      }
    ],
    "total_generated": 0
  },
  "error": null
}
```

---

### 7.4 問題取得

#### GET `/api/v1/problem-groups`（新規問題取得）

- 用途：難易度を指定して、新規問題（未解答の題材）を取得する。模範解答は含まない。
- クエリパラメータ：
  - `difficulty` (required)：`easy | medium | hard`
- 認証：
  - ログイン：必須
  - ゲスト：不要
- 振る舞い：
  - ログイン：
    - 指定された難易度で、当該ユーザーがまだ解いていない題材を在庫から 1 つ払い出す。
    - `problem_group_attempts` から当該ユーザーが解いた問題を判定し、その問題は返さない。
    - 一度解いた問題は二度と払い出されない。
    - ログイン時：成功レスポンス時に `request.session["current_problem_group_id"] = problem_group.id` を保存
    - 該当なしなら 404（在庫不足）を返す。
    - 既に `request.session["current_problem_group_id"]` が存在する場合、`409 Conflict (PROBLEM_IN_PROGRESS)` を返す。
  - ゲスト：
    - 指定された難易度で、在庫からランダムに 1 題材を払い出す。
    - `guest_token` を発行してセッション（`request.session["guest_problem_token"]`）に保持。
    - **ゲストは 1 問のみ払い出し可能で、既に問題を取得済み（セッションに `guest_problem_token` が存在）の場合は 403（GUEST_ALREADY_GENERATED）を返す。**
    - 既に完了済み（`request.session["guest_completed"] == True`）の場合は 403（GUEST_LIMIT_REACHED）を返す。
- Response（200）ログイン例

```json
{
  "data": {
    "kind": "persisted",
    "problem_group": {
      "problem_group_id": 123,
      "title": "...",
      "description": "...",
      "difficulty": "easy"
    },
    "problems": [
      {
        "problem_id": 1,
        "problem_type": "db",
        "order_index": 1,
        "problem_body": "..."
      },
      {
        "problem_id": 2,
        "problem_type": "api",
        "order_index": 2,
        "problem_body": "..."
      }
    ]
  },
  "error": null
}
```

- Response（200）ゲスト例

```json
{
  "data": {
    "kind": "guest",
    "guest_token": "opaque-token",
    "problem_group": {
      "problem_group_id": 123,
      "title": "SNSアプリ",
      "description": "...",
      "difficulty": "easy"
    },
    "problems": [
      {
        "problem_id": 1,
        "problem_group_id": 123,
        "order_index": 1,
        "problem_type": "db",
        "problem_body": "..."
      },
      {
        "problem_id": 2,
        "problem_group_id": 123,
        "order_index": 2,
        "problem_type": "api",
        "problem_body": "..."
      }
    ]
  },
  "error": null
}
```

---

#### GET `/api/v1/problem-groups/{problem_group_id}`（特定題材取得・復習）

- 用途：問題 ID を指定して、特定の題材詳細（problem_group + problems）を取得する。模範解答は含まない。復習など、既に解いた問題を再度確認する際に使用。
- パスパラメータ：
  - `problem_group_id` (required)：取得したい題材の ID
- 認証：
  - ログイン：必須
  - ゲスト：不要（MVP では実装不要。将来的に復習ゲスト機能を追加する場合のみ実装）
- 振る舞い：
  - ログイン：
    - 指定された ID の題材を返す。
    - ユーザーが当該問題を解いているかどうかは関係なく返す（復習用）。
  - ゲスト：MVP では実装不要
- Response（200）

```json
{
  "data": {
    "kind": "persisted",
    "problem_group": {
      "problem_group_id": 123,
      "title": "SNSアプリ",
      "description": "...",
      "difficulty": "easy"
    },
    "problems": [
      {
        "problem_id": 1,
        "problem_group_id": 123,
        "order_index": 1,
        "problem_type": "db",
        "problem_body": "..."
      },
      {
        "problem_id": 2,
        "problem_group_id": 123,
        "order_index": 2,
        "problem_type": "api",
        "problem_body": "..."
      }
    ]
  },
  "error": null
}
```

---

### 7.5 採点・解説（〇 ×△）

> 生成と同様に、ログイン/ゲストを **同一エンドポイントで分岐**する。

#### POST `/api/v1/grade`

- 用途：小問（problem）ごとの解答を提出し、AI 採点（〇 ×△）とユーザー回答に合わせた解説、および模範解答を返す

- 認証：

  - ログイン：解答・採点結果を DB に保存する
  - ゲスト：DB に保存しない（`guest_token` に紐づく一時データで採点する）

- 判定方法（バックエンド）

  - `request.user.is_authenticated` が `True` ならログイン、`False` ならゲスト

- 入力ルール

  - ログイン時：`problem_group_id` 必須
  - ゲスト時：`guest_token` 必須（かつ `guest_token == request.session["guest_problem_token"]` を満たす）
  - `problem_group_id` と `guest_token` は **同時に送らない**（XOR）

- ゲスト制限（1 題材のみ）

  - `request.session["guest_completed"] == True` の場合：`403 (GUEST_LIMIT_REACHED)`
  - 採点では `guest_completed` を変更しない。完了（問題終了）API で `True` にする。
  - 採点は `problem_group_attempts` に書き込まない（完了 API で upsert する）。

- Request（ログイン）

```json
{
  "problem_group_id": 123,
  "answers": [
    { "problem_id": 1, "answer_body": "CREATE TABLE ..." },
    { "problem_id": 2, "answer_body": "def create_post(...): ..." }
  ]
}
```

- Request（ゲスト）

```json
{
  "guest_token": "opaque-token",
  "answers": [
    { "problem_id": 1, "answer_body": "CREATE TABLE ..." },
    { "problem_id": 2, "answer_body": "def create_post(...): ..." }
  ]
}
```

- Response（200）

```json
{
  "data": {
    "results": [
      {
        "problem_ref": { "problem_id": 1, "order_index": 1 },
        "problem_type": "db",
        "grade": 2,
        "grade_display": "○",
        "explanation": {
          "version": 1,
          "explanation_body": "..."
        },
        "model_answer": {
          "version": 1,
          "model_answer": "CREATE TABLE users (...); ..."
        }
      },
      {
        "problem_ref": { "problem_id": 2, "order_index": 2 },
        "problem_type": "api",
        "grade": 1,
        "grade_display": "△",
        "explanation": {
          "version": 1,
          "explanation_body": "..."
        },
        "model_answer": {
          "version": 1,
          "model_answer": "def create_post(...): ..."
        }
      }
    ]
  },
  "error": null
}
```

### 7.6 問題終了（完了ボタン）

> 採点結果を確認した後、フロントの「問題終了」ボタンから呼ばれる API。

#### POST `/api/v1/problem-groups/{problem_group_id}/complete`

- 用途：題材を「解き終わった」ことを明示的に記録し、再払い出しを防ぐ。
- 認証：
  - ログイン：必須。`(problem_group_id, user_id)` を `problem_group_attempts` に upsert（冪等）。成功時に `request.session["current_problem_group_id"]` を削除（クリア）
  - ゲスト：不要。`guest_token` が必須で、セッションの `guest_problem_token` と一致することを確認する。
- 振る舞い：
  - ログイン：問題を払い出した本人のみ upsert を許可し、以後この題材は払い出さない。
  - ゲスト：成功時に `request.session["guest_completed"] = True` を保存し、以後の取得・採点を禁止する。
- Request（ログイン）

```json
{}
```

- Request（ゲスト）

```json
{ "guest_token": "opaque-token" }
```

- Response（200）

```json
{ "data": { "ok": true }, "error": null }
```

---

### 7.7 復習（追加機能：MVP 外だが API の形は想定）

#### GET `/api/v1/problem-groups/mine`

- 用途：自分が解いた題材一覧（復習用）
- 認証：必要
- Query（例）

  - `?cursor=...&difficulty=easy`

- Response（200）

```json
{
  "data": {
    "items": [
      {
        "problem_group_id": 123,
        "title": "SNSアプリ",
        "difficulty": "easy",
        "created_at": "..."
      }
    ],
    "next_cursor": null
  },
  "error": null
}
```

#### GET `/api/v1/problems/{problem_id}/answers`

- 用途：特定小問に対する自分の回答履歴（created_at 降順）
- 認証：必要
- Response（200）

```json
{
  "data": {
    "items": [
      {
        "answer_id": 10,
        "problem_id": 1,
        "answer_body": "...",
        "grade": 2,
        "created_at": "..."
      }
    ]
  },
  "error": null
}
```

---

## 8. フロントエンド方針（概要）

- React + TypeScript による SPA とします。
- 想定されるメイン画面（MVP 時点）：
  - トップ／問題生成画面
    - 難易度・モード選択 → 「問題を生成」ボタン
  - 問題解答画面
    - 問題文表示
    - DB 設計／API 設計の回答フォーム
  - 採点結果画面
    - スコア
    - 模範解答
    - 解説
- ログイン／ゲストは、同じ UI フローで扱います（見た目はほぼ同じ）。
- API との通信は
  - 専用の API クライアントモジュールを作成し、
  - コンポーネントから直接 `fetch` を呼ばない。
    例：`shared/api/client.ts` に共通クライアント、`entities/*/api.ts` にドメインごとの関数をまとめる。

---

## 9. コーディング規約

### 9.1 Python / Django

- **スタイル**
  - PEP8 準拠
  - 可能な限り、すべての関数・メソッドに型ヒントを付与する。
- **フレームワークの使い方**
  - Web API は Django REST Framework（DRF）を使用する。
  - HTML テンプレートレンダリングは行わず、JSON API のみにする。
  - ビジネスロジックは View から切り出し、サービス層やユースケース関数にまとめることを優先する。
- **命名・設計**
  - モデル名・フィールド名・変数名は英語。
  - DB テーブル・カラムもモデルに合わせて英語で統一する。
  - 設定値（シークレット・DB 接続情報など）は環境変数から読み込む。

### 9.2 TypeScript / React

- **スタイル**
  - 関数コンポーネント＋ Hooks を使用する（クラスコンポーネントは使用しない）。
  - `any` の使用は原則禁止。
    - やむを得ず使用する場合は `// TODO: 型を絞る` コメントを付ける。
  - ESLint / Prettier が通るコードのみをコミットする。
- **構成**
  - “画面＝ pages、操作＝ features、ドメイン＝ entities、共通＝ shared” を基本として配置する。
  - API クライアント・型定義は `shared/api/`・`entities/` に集約し、UI 層から直接 `fetch` を呼ばない。
- **命名**
  - コンポーネント名・型名・インターフェース名は `PascalCase`。
  - ファイル名は `kebab-case` または `camelCase` に統一する（プロジェクト内の既存方針に合わせる）。

### 9.3 共通（Python / TypeScript）

- 既存関数・クラスのシグネチャや挙動を変更する場合は、
  - なぜ変更が必要なのかをコメントまたは Docstring に残してから変更する。
- コメントは「何をしているか」よりも「なぜそうしているか」を優先して書く。
- Conventional Commits（config-conventional）に準じたコミットメッセージ、かつ、フロントエンド・バックエンドともにリンタ・フォーマッタのチェックを満たさないとコミットできないようにしています。

  - **pre-commit**：frontend（ESLint + Prettier）／backend（Ruff format + Ruff check）
  - **commit-msg**：commitlint（Conventional Commits）

- コマンドは各種 README.md に記載しています。

---

## 10. このファイルの使い方

- このファイルに書かれているのは、**mondAI プロジェクトの前提・設計方針・MVP と追加機能の境界**です。
- **MVP セクションに書かれているものを最優先**で実装してください。
- 追加機能は、明示的に指示があった場合にのみ着手する想定です。
