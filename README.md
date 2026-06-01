<!-- AI_README_SETUP_GUIDE_START -->
## 🧭 画像付き初期設定ガイド

![README 画像付き初期設定ガイド](docs/assets/readme-setup-guide.svg)

このリポジトリ **facebook-auto-post** を初めて開いた人は、まずここだけ見れば初期設定から実行、成果物確認まで進められます。

### 最初にやること

1. 必要なSecretや外部サービス設定を確認します。
2. GitHub Actions または README の実行手順に沿って動かします。
3. 実行ログと成果物を確認します。
4. エラー時は Actions の失敗ステップと Secret名を確認します。

### 詳しい画像付きガイド

- [docs/setup-visual-guide.md](docs/setup-visual-guide.md)
- [docs/image-generation-prompts.md](docs/image-generation-prompts.md)

> SecretやAPIキーの実値は、README、Issue、ログ、画像に絶対に貼らないでください。例では `********` または `YOUR_SECRET_HERE` を使います。

<!-- AI_README_SETUP_GUIDE_END -->


# Facebook Auto Post

Facebookページへ自動投稿するためのPython CLIです。GitHub Actionsで毎日投稿し、手動実行もできます。

> 注意: このツールはFacebook **ページ**への投稿を対象にしています。個人プロフィールへの自動投稿ではありません。

## まず読むもの

- [事前設定ガイド（初心者向け）](docs/PRESETTINGS_ja.md)
- [Smoke Test Workflow](.github/workflows/facebook-smoke-test.yml)

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

### Smoke Test

`.github/workflows/facebook-smoke-test.yml` は以下を確認します。

- pytest
- `DRY_RUN=true`で投稿コマンド確認
- `FB_PAGE_ID` / `FB_PAGE_ACCESS_TOKEN` の有無確認

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
│   ├── facebook-post.yml
│   └── facebook-smoke-test.yml
├── docs/
│   └── PRESETTINGS_ja.md
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
