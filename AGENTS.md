# AGENTS.md

## 1. プロジェクト概要

### プロダクト名

* **mondAI**

### コンセプト

* バックエンドエンジニア（特に経験が浅い人）向けの
  * **データベース設計**
  * **API設計**
* に特化した「設計問題練習用 Web アプリ」です。
* SNSアプリなど、現実的な題材を元に
  * 問題を生成し
  * 回答を書き
  * AIで採点と解説を返す
    という流れを繰り返すことで、設計の引き出しを増やすことを目標とします。

### 想定ユーザー

* Webバックエンド初学者
* 就活の面接で「DB設計・API設計」の問題対策をしたいエンジニア学生
* 自分の設計力を定期的にチェックしたい初〜中級エンジニア

---

## 2. 審査観点とプロダクトのゴール

本プロジェクトは「技育ハッカソン」に出場するためのものです。
審査は **オーディエンス投票方式** で行われ、主に以下の観点が見られます。

### 2.1 審査基準（要約）

1. **サービスとしての価値**
   * 世の中の役に立つか
   * 面白い・触っていて楽しいか
2. **サービスの完成度**
   * 実装されている機能が一通り使えるか
   * UI / UX が直感的でストレスなく操作できるか
3. **技術的な挑戦**
   * 新しい / 難しい技術にチャレンジしているか
   * 設計や実装に工夫が見られるか

### 2.2 mondAI として目指す方向

* **価値**
  * 「DB・API設計」という抽象的になりがちなテーマを、**具体的な問題演習**として体験できること
  * 面接対策としてもそのまま使えるような、現実に近い題材の問題を用意すること
* **完成度**
  * ゲストでもワンクリックで問題を解いて遊べる
  * ログインユーザーは自分の回答・スコアを蓄積できる（データとして）
* **技術的な挑戦**
  * 問題生成と採点・解説に AI を活用する
  * DB スキーマ・API 設計自体も「ちゃんとした設計」を目指す

---

## 3. 開発スタック・構成方針

### 3.1 技術スタック

* **バックエンド**
  * Python / Django
  * Django REST Framework（DRF）で JSON API を提供
  * パッケージ管理：`uv`
  * Lint・Format：`Ruff`
* **データベース**
  * **PostgreSQL 16**（開発・本番ともに Postgres 前提）
* **フロントエンド**
  * React
  * TypeScript
  * Lint：`ESLint`
  * Format：`Prettier`

### 3.2 リポジトリ構成（モノレポ）

* `backend/`
  * Django プロジェクト・アプリケーション
  * DRF を用いた API 実装（ドメイン分割）
* `frontend/`
  * React + TypeScript の SPA
  * バックエンドの REST API を叩くクライアント

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
````

#### frontend（FSD軽量版：pages + features + entities + shared）

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

* メールアドレス＋パスワードによる
  * ユーザー登録
  * ログイン
  * ログアウト
* ログインユーザーの「生成した問題」「回答」「採点結果」は **DB に永続保存**する。

#### ゲストモード

* 会員登録なしで、「すぐに問題を 1 問解いてみる」ことができる。
* **ゲストは 1 問だけ**（問題生成→回答→採点・解説まで）。1問解いた後は登録/ログインを促し、これ以上は解けないようにする。
* ゲストユーザーの「問題」「回答」「採点結果」は **永続保存しない**（cookie/session 等の一時状態でのみ保持）。
* ゲストとログインユーザーの両方で、同じ UI の流れを辿れることが望ましい。

### 4.2 問題生成

ユーザー（ログイン or ゲスト）は、以下を指定して問題を生成する：

* **難易度**
  * `easy | medium | hard`
* **問題（サービス）規模**
  * `small | medium | large`
* **モード**
  * `db_only`：DB設計問題だけ
  * `api_only`：API設計問題だけ
  * `both`：DB・API両方の設計問題

AI により、以下のような構造の問題を生成する：

* アプリの概要説明（例：SNSアプリ、ECサイトなど）
* 設計問題パート
  * DB 設計問題（必要テーブル・カラム・制約などを SQL ライクに記述させる）
  * API 設計問題（擬似コードで API を実装させる）
* モードに応じて、DB / API どちらを含めるかが変わる。

**ログインユーザーの場合：**

* 生成された問題は `Problem` レコードとして DB に保存する。

**ゲストユーザーの場合：**

* 問題は DB に保存せず、その場限りの一時データとして扱う。

### 4.3 問題回答

問題に対して、ユーザーは以下のように回答する：

* `db_only` モード
  * DB設計回答（SQLライクなDDL）を入力するテキストエリア
* `api_only` モード
  * API設計回答（擬似コード）を入力するテキストエリア
* `both` モード
  * 上記 2 つの入力欄を両方表示

**ログインユーザーの場合：**

* 回答は `Answer`（または同等のモデル）として DB に保存する。
* 後の復習や分析に使えるよう、問題との紐付けも保存しておく。

**ゲストユーザーの場合：**

* 回答は永続保存せず、その場の画面表示のためだけに持つ。

### 4.4 採点・解説

AI による自動採点と解説表示を行う。

* 採点は、**マルバツサンカク（〇×△）**で行う。
* 採点と同時に、模範解答（DB設計例・API擬似コード例）と解説テキストを表示する。
* ログインユーザーの場合：
  * 採点結果・模範解答・解説は `Answer` レコード等に紐づけて保存しておく。
* ゲストユーザーの場合：
  * 採点結果等は永続保存せず、その問題画面でのみ表示する。

---

## 5. 追加機能（MVP外）

ここに記載する機能は、「時間があれば実装したいが MVP ではない」ものです。

### 5.1 優先度 High の追加機能

* **ユーザープロフィール**
  * 表示名・アイコン・自己紹介などを登録・編集できる画面
* **復習画面（マイ問題一覧）**
  * ログインユーザーが過去に解いた問題の一覧
  * 各問題ごとに「問題文」「自分の回答」「採点結果」「模範解答・解説」を確認できる。
  * 難易度や解いた日時でソート／簡易フィルタ（タグではなく難易度などで絞り込む）。
* **問題の再挑戦機能**
  * 過去の問題に対して、再度回答を送ることができる。
  * 再回答をどのように保存するか（複数回答履歴を持つか）は別途設計。
* **問題評価**
  * ユーザーが問題に対して評価（例：5段階評価・Likeボタンなど）を付ける。
  * 評価は後のプロンプト改善や「みんなの問題」表示条件に利用する。

### 5.2 優先度 Medium の追加機能

* **みんなの問題**
  * 他のユーザーが生成し、かつ高評価した問題の一覧ページ。
  * 自分で生成した問題と同様に解答できる。
* **ステータス画面**
  * ユーザーごとの
    * 解いた問題数
    * 平均採点結果
    * 難易度ごとの傾向
      などを可視化する。
* **ランキング**
  * 総スコアや解答数などに基づく簡易ランキング。
  * ハッカソンの演出として、トップページなどから見える形が望ましい。
* **採点結果の手動修正・再採点**
  * AI 採点が明らかにおかしい場合に、ユーザーが手動で採点結果を修正できる。
  * 修正履歴を保存し、AI 採点とユーザー修正との差分を後で分析できるようにする。

### 5.3 優先度 Low の追加機能

* **ゲストから本登録への引き継ぎ**
  * ゲストで解いた問題・回答を、後からユーザー登録した際に引き継ぐ。
* **より細かいフィルタ・検索**
  * 難易度・作成日時などによる絞り込み。

---

## 6. DB設計

### users

* user_id (PK)
* name
* email (UNIQUE)
* password_hash
* icon_url (NULL可)
* created_at
* updated_at

### problem_groups（題材）

* problem_group_id (PK)
* title
* description
* difficulty（easy/medium/hard）
* app_scale（small/medium/large）
* mode（db_only/api_only/both）
* created_by_user_id (FK → users.user_id)
* created_at
* updated_at
* CHECK(problem_type IN ('easy','medium','hard'))
* CHECK(problem_type IN ('small','medium','large'))
* CHECK(problem_type IN ('db_only','api_only','both'))

### problems（題材内の小問）

* problem_id (PK)
* problem_group_id (FK → problem_groups.problem_group_id)
* problem_body
* problem_type（db/api）
* order_index（題材内で何問目か）
* created_at
* updated_at
* UNIQUE(problem_group_id, order_index)
* CHECK(problem_type IN ('db','api'))

### answers（小問に対する回答）

* answer_id (PK)
* problem_id (FK → problems.problem_id)
* user_id (FK → users.user_id)
* answer_body
* grade（0/1/2 = ×/△/○）
* created_at
* updated_at
* CHECK(problem_type IN (0,1,2))


### problem_solutions（小問に対する模範解答・解説）

* problem_id (PK, FK → problems.problem_id)
* version (PK)
* solution_body
* explanation
* created_at
* updated_at

### problems_groups_evaluation（題材への評価）

* user_id (PK, FK → users.user_id)
* problem_group_id (PK, FK → problem_groups.problem_group_id)
* evaluation（高評価・低評価）※enum等で型を確定
* evaluation_reason（NULL可）
* created_at
* updated_at
* CHECK(evaluation IN (低評価,高評価))

### favorite_problems_groups（お気に入り）

* user_id (PK, FK → users.user_id)
* problem_group_id (PK, FK → problem_groups.problem_group_id)
* created_at
* updated_at

### sessions

* Django の標準（`django_session`）を使う前提
  ※自前テーブルは作らない

---

## 7. API設計（MVP）

### 7.1 共通仕様

- Base URL：`/api/v1`
- 形式：REST / JSON
- 認証：Django 標準のログイン（セッションCookie）を利用
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

### 7.2 認証（Djangoセッション）

> SPA から安全に POST を行うため、CSRFトークン取得用エンドポイントを用意する。

#### GET `/api/v1/auth/csrf`
- 用途：CSRF Cookie を発行・取得する
- 認証：不要
- Response（200）
```json
{
  "data": { "csrfToken": "..." },
  "error": null
}
````

#### POST `/api/v1/auth/register`

* 用途：ユーザー新規登録
* 認証：不要
* Request

```json
{
  "email": "user@example.com",
  "password": "password",
  "name": "mondai user"
}
```

* Response（201）

```json
{
  "data": { "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" } },
  "error": null
}
```

#### POST `/api/v1/auth/login`

* 用途：ログイン（セッション確立）
* 認証：不要
* Request

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

* Response（200）

```json
{
  "data": { "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" } },
  "error": null
}
```

#### POST `/api/v1/auth/logout`

* 用途：ログアウト（セッション破棄）
* 認証：必要
* Response（200）

```json
{
  "data": { "ok": true },
  "error": null
}
```

#### GET `/api/v1/auth/me`

* 用途：ログイン中ユーザー情報取得
* 認証：必要
* Response（200）

```json
{
  "data": { "user": { "user_id": 1, "email": "user@example.com", "name": "mondai user" } },
  "error": null
}
```

---

### 7.3 問題生成（題材 + 小問）

#### POST `/api/v1/problem-groups/generate`

- 用途：題材（problem_group）と小問（problems）を AI で生成する
- 認証：
  - ログイン：生成結果を DB に保存する
  - ゲスト：DBに保存しない（短命トークンで一時参照）
- 判定方法（バックエンド）
  - `request.user.is_authenticated` が `True` ならログイン、`False` ならゲスト

- ゲスト制限（1題材のみ）
  - 生成成功時に `request.session["guest_problem_token"] = <guest_token>` を保存し、以後の再生成を禁止する
  - 採点成功時に `request.session["guest_completed"] = True` を保存し、以後は生成・採点とも禁止する
  - `request.session["guest_completed"] == True` の場合：`403 (GUEST_LIMIT_REACHED)`
  - `request.session["guest_problem_token"]` が既に存在する場合：`403 (GUEST_ALREADY_GENERATED)`

- Request
```json
{
  "difficulty": "easy",
  "app_scale": "small",
  "mode": "both"
}
````

* Response（200）ログイン時（永続化）

```json
{
  "data": {
    "kind": "persisted",
    "problem_group": {
      "problem_group_id": 123,
      "title": "SNSアプリ",
      "description": "...",
      "difficulty": "easy",
      "app_scale": "small",
      "mode": "both",
      "created_at": "2025-12-12T00:00:00Z"
    },
    "problems": [
      { "problem_id": 1, "problem_group_id": 123, "problem_type": "db",  "order_index": 1, "problem_body": "..." },
      { "problem_id": 2, "problem_group_id": 123, "problem_type": "api", "order_index": 2, "problem_body": "..." }
    ]
  },
  "error": null
}
```

* Response（200）ゲスト時（非永続）

  * `guest_token` は「この1題材の生成結果」をサーバ側で一時参照するためのトークン（短命想定）
  * レスポンス返却前に `request.session["guest_problem_token"] = guest_token` を保存する

```json
{
  "data": {
    "kind": "guest",
    "guest_token": "opaque-token",
    "problem_group": {
      "title": "SNSアプリ",
      "description": "...",
      "difficulty": "easy",
      "app_scale": "small",
      "mode": "both"
    },
    "problems": [
      { "order_index": 1, "problem_type": "db",  "problem_body": "..." },
      { "order_index": 2, "problem_type": "api", "problem_body": "..." }
    ]
  },
  "error": null
}
```

---

### 7.4 解答・採点（〇×△）

> 生成と同様に、ログイン/ゲストを **同一エンドポイントで分岐**する。

#### POST `/api/v1/grade`

* 用途：小問（problem）ごとの解答を提出し、AI採点（〇×△）と模範解答・解説を返す

* 認証：

  * ログイン：解答・採点結果を DB に保存する
  * ゲスト：DBに保存しない（`guest_token` に紐づく一時データで採点する）

* 判定方法（バックエンド）

  * `request.user.is_authenticated` が `True` ならログイン、`False` ならゲスト

* 入力ルール

  * ログイン時：`problem_group_id` 必須
  * ゲスト時：`guest_token` 必須（かつ `guest_token == request.session["guest_problem_token"]` を満たす）
  * `problem_group_id` と `guest_token` は **同時に送らない**（XOR）

* ゲスト制限（1題材のみ）

  * `request.session["guest_completed"] == True` の場合：`403 (GUEST_LIMIT_REACHED)`
  * 採点が成功したら `request.session["guest_completed"] = True` を保存し、以後は生成・採点とも禁止する

* Request（ログイン）

```json
{
  "problem_group_id": 123,
  "answers": [
    { "problem_id": 1, "answer_body": "CREATE TABLE ..." },
    { "problem_id": 2, "answer_body": "def create_post(...): ..." }
  ]
}
```

* Request（ゲスト）

```json
{
  "guest_token": "opaque-token",
  "answers": [
    { "order_index": 1, "answer_body": "CREATE TABLE ..." },
    { "order_index": 2, "answer_body": "def create_post(...): ..." }
  ]
}
```

* Response（200）

```json
{
  "data": {
    "results": [
      {
        "problem_ref": { "problem_id": 1, "order_index": 1 },
        "problem_type": "db",
        "grade": 2,
        "solution": { "version": 1, "solution_body": "...", "explanation": "..." }
      },
      {
        "problem_ref": { "problem_id": 2, "order_index": 2 },
        "problem_type": "api",
        "grade": 1,
        "solution": { "version": 1, "solution_body": "...", "explanation": "..." }
      }
    ]
  },
  "error": null
}
```

---

### 7.5 復習（追加機能：MVP外だがAPIの形は想定）

#### GET `/api/v1/problem-groups/mine`

* 用途：自分が生成した題材一覧（復習用）
* 認証：必要
* Query（例）

  * `?cursor=...&difficulty=easy&mode=both`
* Response（200）

```json
{
  "data": {
    "items": [
      { "problem_group_id": 123, "title": "SNSアプリ", "difficulty": "easy", "app_scale": "small", "mode": "both", "created_at": "..." }
    ],
    "next_cursor": null
  },
  "error": null
}
```

#### GET `/api/v1/problem-groups/{problem_group_id}`

* 用途：題材詳細（problem_group + problems）
* 認証：必要（将来 public 化するなら要調整）
* Response（200）

```json
{
  "data": {
    "problem_group": { "problem_group_id": 123, "title": "...", "description": "...", "difficulty": "easy", "app_scale": "small", "mode": "both" },
    "problems": [
      { "problem_id": 1, "problem_type": "db", "order_index": 1, "problem_body": "..." }
    ]
  },
  "error": null
}
```

#### GET `/api/v1/problems/{problem_id}/answers`

* 用途：特定小問に対する自分の回答履歴（created_at 降順）
* 認証：必要
* Response（200）

```json
{
  "data": {
    "items": [
      { "answer_id": 10, "problem_id": 1, "answer_body": "...", "grade": 2, "created_at": "..." }
    ]
  },
  "error": null
}
```

---

## 8. フロントエンド方針（概要）

* React + TypeScript による SPA とします。
* 想定されるメイン画面（MVP 時点）：
  * トップ／問題生成画面
    * 難易度・モード選択 → 「問題を生成」ボタン
  * 問題解答画面
    * 問題文表示
    * DB設計／API設計の回答フォーム
  * 採点結果画面
    * スコア
    * 模範解答
    * 解説
* ログイン／ゲストは、同じ UI フローで扱います（見た目はほぼ同じ）。
* API との通信は
  * 専用の API クライアントモジュールを作成し、
  * コンポーネントから直接 `fetch` を呼ばない。
    例：`shared/api/client.ts` に共通クライアント、`entities/*/api.ts` にドメインごとの関数をまとめる。

---

## 9. コーディング規約

### 9.1 Python / Django

* **スタイル**
  * PEP8 準拠
  * 可能な限り、すべての関数・メソッドに型ヒントを付与する。
* **フレームワークの使い方**
  * Web API は Django REST Framework（DRF）を使用する。
  * HTML テンプレートレンダリングは行わず、JSON API のみにする。
  * ビジネスロジックは View から切り出し、サービス層やユースケース関数にまとめることを優先する。
* **命名・設計**
  * モデル名・フィールド名・変数名は英語。
  * DB テーブル・カラムもモデルに合わせて英語で統一する。
  * 設定値（シークレット・DB 接続情報など）は環境変数から読み込む。

### 9.2 TypeScript / React

* **スタイル**
  * 関数コンポーネント＋Hooks を使用する（クラスコンポーネントは使用しない）。
  * `any` の使用は原則禁止。
    * やむを得ず使用する場合は `// TODO: 型を絞る` コメントを付ける。
  * ESLint / Prettier が通るコードのみをコミットする。
* **構成**
  * “画面＝pages、操作＝features、ドメイン＝entities、共通＝shared” を基本として配置する。
  * API クライアント・型定義は `shared/api/`・`entities/` に集約し、UI層から直接 `fetch` を呼ばない。
* **命名**
  * コンポーネント名・型名・インターフェース名は `PascalCase`。
  * ファイル名は `kebab-case` または `camelCase` に統一する（プロジェクト内の既存方針に合わせる）。

### 9.3 共通（Python / TypeScript）

* 既存関数・クラスのシグネチャや挙動を変更する場合は、
  * なぜ変更が必要なのかをコメントまたは Docstring に残してから変更する。
* コメントは「何をしているか」よりも「なぜそうしているか」を優先して書く。
* Conventional Commits（config-conventional）に準じたコミットメッセージ、かつ、フロントエンド・バックエンドともにリンタ・フォーマッタのチェックを満たさないとコミットできないようにしています。

  * **pre-commit**：frontend（ESLint + Prettier）／backend（Ruff format + Ruff check）
  * **commit-msg**：commitlint（Conventional Commits）

* コマンドは各種 README.md に記載しています。
---

## 10. このファイルの使い方

* このファイルに書かれているのは、**mondAI プロジェクトの前提・設計方針・MVPと追加機能の境界**です。
* **MVP セクションに書かれているものを最優先**で実装してください。
* 追加機能は、明示的に指示があった場合にのみ着手する想定です。
