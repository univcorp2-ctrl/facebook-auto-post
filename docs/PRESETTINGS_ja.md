# Facebook Auto Post 事前設定ガイド

このrepoでFacebookページへ自動投稿する前に必要な設定を、初心者向けに整理します。

## まず必要なもの

| 必要なもの | 用途 | 必須 |
| --- | --- | --- |
| Facebookページ | 投稿先。個人プロフィールではなくページが必要 | yes |
| Metaアプリ | Facebook Graph APIを使うため | yes |
| Page ID | 投稿先ページを指定するため | yes |
| Page Access Token | 投稿権限つきのトークン | yes |
| GitHub Secrets | Tokenを安全に保存するため | yes |
| posts/posts.json | 投稿内容を管理するファイル | yes |

## GitHubに設定するSecrets

GitHub repoで以下を設定してください。

場所:

```text
GitHub repo
→ Settings
→ Secrets and variables
→ Actions
→ Repository secrets
```

登録するSecrets:

```text
FB_PAGE_ID=投稿先FacebookページID
FB_PAGE_ACCESS_TOKEN=Page access token
```

任意のVariables:

```text
FB_GRAPH_VERSION=v25.0
```

## 投稿内容の編集

`posts/posts.json` を編集します。

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

## 安全な確認順序

いきなり本番投稿せず、以下の順番で確認してください。

```text
1. Facebook posting smoke test を実行
2. DRY_RUN=true で投稿コマンドが動くか確認
3. GitHub Secrets が入っているか確認
4. Facebook scheduled post を手動実行
5. dry_run=false にして本番投稿
```

## Actionsの使い方

### 1. 安全確認

```text
Actions
→ Facebook posting smoke test
→ Run workflow
```

このworkflowは投稿しません。テスト、dry-run、Secrets有無を確認します。

### 2. 本番投稿

```text
Actions
→ Facebook scheduled post
→ Run workflow
```

入力例:

```text
dry_run=false
message=テスト投稿です
link=https://example.com
```

## トラブル時の確認

| 症状 | 確認すること |
| --- | --- |
| 投稿されない | `dry_run=false` になっているか |
| Tokenエラー | `FB_PAGE_ACCESS_TOKEN` が正しいか |
| Page IDエラー | `FB_PAGE_ID` が正しいか |
| 権限エラー | Page tokenに投稿権限があるか |
| Actionsで失敗 | Actionsログのエラー本文を見る |

## 注意

- 対象はFacebookページです。個人プロフィールへの自動投稿ではありません。
- TokenはREADMEやコードに直接書かないでください。
- 本番投稿の前に必ずsmoke testを実行してください。
