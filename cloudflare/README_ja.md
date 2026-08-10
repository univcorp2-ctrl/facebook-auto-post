# Cloudflare Workers AI版 Facebook自動投稿

`facebook-auto-post` を Cloudflare Cron + Workers AI + Facebook Graph API で無人実行する構成です。

## 処理フロー

```text
Cloudflare Cron (毎日09:17 JST)
  -> Worker scheduled()
  -> posts/posts.json から当日の元投稿を選択
  -> Workers AI で自然な日本語にリライト
  -> 文字数・空文字を検証
  -> Facebook Graph API へ投稿

Workers AI が失敗した場合
  -> 元の posts/posts.json の文章へフォールバック
  -> Facebook Graph API へ投稿
```

既定モデルは、多言語対応とコストのバランスを重視して `@cf/qwen/qwen3-30b-a3b-fp8` を使います。`AI_MODEL` を変更すれば `@cf/openai/gpt-oss-120b` など別の Workers AI モデルにも切り替えられます。

## Wrangler設定

`wrangler.jsonc` に Workers AI binding を設定しています。

```json
"ai": {
  "binding": "AI"
}
```

Cron Trigger は `17 0 * * *`（UTC）で、毎日09:17 JSTに実行します。

## Worker Secrets

Cloudflare側に次をSecretとして設定します。値をGitHubへコミットしないでください。

- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `CUSTOM_GPT_SHARED_SECRET`

Workers AI自体は `AI` binding を使うため、別のLLM APIキーは不要です。

## 通常変数

- `FB_GRAPH_VERSION=v25.0`
- `POSTS_URL=https://raw.githubusercontent.com/univcorp2-ctrl/facebook-auto-post/main/posts/posts.json`
- `AI_ENABLED=true`
- `AI_FALLBACK=true`
- `AI_MODEL=@cf/qwen/qwen3-30b-a3b-fp8`

任意で `AI_POST_INSTRUCTION` を設定すると、投稿生成時に追加指示を渡せます。

## 手動実行 / Custom GPT Action

`POST /post` を呼びます。`Authorization: Bearer <CUSTOM_GPT_SHARED_SECRET>` が必要です。

```json
{
  "dry_run": true,
  "use_ai": true
}
```

`dry_run=true` なら Workers AI で文章を生成しますがFacebookには投稿しません。

主なオプション:

- `message`: 指定するとAI生成をせず、その文章を投稿対象にする
- `link`: `message` と一緒に任意リンクを指定
- `post_index`: `posts.json` の元投稿番号を指定
- `use_ai`: `false` ならAIを使わず元投稿を使用
- `ai_model`: 1回だけ別モデルを使用
- `ai_instruction`: 1回だけ追加の生成指示を指定
- `dry_run`: `true` ならFacebook投稿を行わず生成結果だけ返す

## 安全策

Workers AIには、元投稿にない数字・実績・価格・人物・会社情報・投資成果を新しく作らないよう指示しています。生成結果が空、短すぎる、長すぎる、またはWorkers AI呼び出しが失敗した場合は、`AI_FALLBACK=true` なら元投稿を使用します。

Cloudflare本番デプロイとFacebook投稿成功を確認するまでは、既存GitHub Actionsのscheduleを無効化しません。成功後にGitHub側scheduleを停止して二重投稿を防ぎます。
