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
