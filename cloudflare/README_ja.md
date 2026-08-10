# Cloudflare Workers版 Facebook自動投稿

`facebook-auto-post` の既存投稿ロジックをCloudflare Workersから実行する構成です。

- Cron Trigger: `17 0 * * *`（毎日09:17 JST）
- 投稿データ: `posts/posts.json` をGitHub Rawから取得
- 投稿先: Facebook Graph API `/{page-id}/feed`
- 手動実行: `POST /post`
- ヘルス確認: `GET /health`

## Cloudflare Worker Secrets

Cloudflare側に次のSecretを設定します。値をGitHubへコミットしないでください。

- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `CUSTOM_GPT_SHARED_SECRET`

通常変数は `wrangler.jsonc` で管理します。

- `FB_GRAPH_VERSION=v25.0`
- `POSTS_URL=https://raw.githubusercontent.com/univcorp2-ctrl/facebook-auto-post/main/posts/posts.json`

## カスタムGPTからの実行

Custom GPT Actionの認証ヘッダーに `Authorization: Bearer <CUSTOM_GPT_SHARED_SECRET>` を設定し、Workerの `POST /post` を呼びます。

JSON例:

```json
{
  "message": "任意の投稿文",
  "link": "https://example.com",
  "dry_run": false
}
```

`message` を省略すると、定期実行と同じく `posts/posts.json` から当日の投稿を選択します。`post_index` を指定すれば任意の投稿番号を選べます。

GitHub Actionsの既存scheduleは、Cloudflareへの本番デプロイとFacebook投稿成功を確認してから無効化してください。二重投稿防止のため、確認前に両方を本番定期実行しないことを推奨します。
