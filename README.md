# Facebook Auto Post

Facebookページへ自動投稿するためのPython CLIです。GitHub Actionsで毎日投稿し、手動実行もできます。

> 注意: このツールはFacebook **ページ**への投稿を対象にしています。個人プロフィールへの自動投稿ではありません。

## 機能

- Facebook Graph APIのPage Feedへテキスト投稿
- 任意でリンク付き投稿
- `posts/posts.json`から日替わりで投稿内容を選択
- `POST_TEXT` / `POST_LINK`による一回限りの上書き投稿
- `DRY_RUN=true`で投稿せず内容確認
- GitHub ActionsによるCIと定期実行
- pytestによるユニットテスト

## 必要なFacebook設定

Meta for Developersでアプリを作成し、対象ページへ投稿できるPage access tokenを用意してください。通常、ページ投稿にはPage ID、Page access token、`pages_manage_posts`、`pages_read_engagement`などの権限が必要です。アプリの状態や権限レビュー要否はMeta側の設定に依存します。

## GitHub Secrets

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録してください。

| Name | Required | Description |
| --- | --- | --- |
| `FB_PAGE_ID` | yes | 投稿先FacebookページID |
| `FB_PAGE_ACCESS_TOKEN` | yes | Page access token |

任意でRepository Variablesに以下を設定できます。

| Name | Default | Description |
| --- | --- | --- |
| `FB_GRAPH_VERSION` | `v25.0` | 使用するGraph APIバージョン |

## 投稿内容の編集

`posts/posts.json`を編集してください。

```json
{
  "posts": [
    {
      "message": "今日のお知らせです。",
      "link": "https://example.com"
    },
    {
      "message": "リンクなし投稿もできます。"
    }
  ]
}
```

定期実行では日付に応じて投稿が選択されます。手動実行時は`post_index`を指定すると特定の投稿を選べます。

## ローカル実行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env`を読み込む場合はシェル側でexportしてください。

```bash
export FB_PAGE_ID="your-page-id"
export FB_PAGE_ACCESS_TOKEN="your-page-access-token"
python -m facebook_auto_post --dry-run
python -m facebook_auto_post
```

一回だけ投稿内容を上書きする例:

```bash
POST_TEXT="こんにちは、自動投稿です" POST_LINK="https://example.com" python -m facebook_auto_post
```

## GitHub Actions

### CI

`.github/workflows/ci.yml` がpush / pull requestでテストを実行します。

### 自動投稿

`.github/workflows/facebook-post.yml` が以下で実行されます。

- `workflow_dispatch`: GitHub UIから手動実行
- `schedule`: 毎日 00:17 UTC、つまり日本時間 09:17 頃に実行

GitHub Actionsのスケジュール実行は混雑時に遅延する場合があります。

## テスト

```bash
pytest
```

## ディレクトリ構成

```text
.
├── .github/workflows/
│   ├── ci.yml
│   └── facebook-post.yml
├── posts/posts.json
├── src/facebook_auto_post/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── client.py
│   ├── config.py
│   └── content.py
└── tests/
    ├── test_client.py
    └── test_content.py
```
