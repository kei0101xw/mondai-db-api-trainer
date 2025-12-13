# バックエンド（Django）

## ■ リポジトリの Clone 後 / Pull 後に行うこと

`backend/`で以下を実行し、仮想環境と依存関係を反映する

```bash
uv sync
```

## ■ ローカルサーバーの起動

```bash
uv run python manage.py runserver
```

## ■Python のバージョン管理について

### Python 本体のインストール

```bash
uv python install (バージョン)
```

### インストール済みバージョンの確認

```bash
uv python list
```

### プロジェクトで使うバージョンの固定

```bash
uv python pin (バージョン)
```

## ■ パッケージの管理

### パッケージの依存関係を同期する場合

```bash
uv sync
```

### パッケージをインストールする場合

```bash
uv add (パッケージ名)
```

### パッケージを削除する場合

```bash
uv remove (パッケージ名)
```

## ■ 機能を追加する時

`backend/`で以下を実行

```bash
uv run python manage.py startapp (機能名)
```

## ■ マイグレーション系コマンド

```bash
# 変更差分からマイグレーションファイル作成
uv run python manage.py makemigrations

# DBへ反映
uv run python manage.py migrate
```

確認系：

```bash
# 適用状況の一覧
uv run python manage.py showmigrations

# 生成されるSQLを確認（例: app_name の 0001 を見る）
uv run python manage.py sqlmigrate app_name 0001
```

## ■ 管理者ユーザー作成・管理画面確認

```bash
# 管理者ユーザー作成
uv run python manage.py createsuperuser
```

サーバー起動後、管理画面にアクセス：

* `http://127.0.0.1:8000/admin/`

## ■ Lint / Format の実行方法

```bash
# フォーマット
uv run ruff format

# Lint（自動修正なし）
uv run ruff check

# Lint（可能な範囲で自動修正）
uv run ruff check --fix
```

## ■ 便利コマンド

```bash
# Djangoのシェル（動作確認・デバッグ用）
uv run python manage.py shell

# DBシェル（PostgreSQLに直接入る）
uv run python manage.py dbshell

# 設定ミスなどの簡易チェック
uv run python manage.py check
```
