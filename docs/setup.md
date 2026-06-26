# Setup Guide

## 1. Notion Data Sourceを作成

Notionで新しいデータベースを作り、可能なら `docs/notion-schema.md` の推奨プロパティを作成します。最低限は以下です。

| 名前 | 型 |
|---|---|
| 物件名 | Title |
| 外部ID | Rich text |

Notion API 2026-03-11ではDatabase IDとData Source IDが分かれています。`NOTION_DATA_SOURCE_ID` を使うのが推奨です。

## 2. Notion Integrationを作成

1. NotionのDeveloper portalでInternal integrationを作成します。
2. Capabilitiesで少なくとも以下を有効にします。
   - Read content
   - Insert content
3. 作成したIntegrationを対象Data Sourceに `Add connections` で追加します。
4. APIキーをGitHub Secret `NOTION_API_KEY` に登録します。
5. Data Source IDをGitHub SecretまたはVariable `NOTION_DATA_SOURCE_ID` に登録します。

## 3. GitHub Actionsに登録する値

Repository Settings → Secrets and variables → Actions で設定します。

### Secrets

| Name | Required | Description |
|---|---:|---|
| `NOTION_API_KEY` | yes | Notion Integration secret |
| `NOTION_DATA_SOURCE_ID` | yes | Notion Data Source ID |
| `FB_PAGE_ID` | Facebook投稿時のみ | FacebookページID |
| `FB_PAGE_ACCESS_TOKEN` | Facebook投稿時のみ | Facebook Page access token |

### Variables

| Name | Default | Description |
|---|---|---|
| `NOTION_SYNC` | `false` | `true` でNotion登録を有効化 |
| `PROPERTY_SYNC_DRY_RUN` | `true` | `false` で本登録 |
| `PROPERTY_SOURCE_PATH` | `samples/community_posts.csv` | 取り込み元CSV/JSON |
| `PROPERTY_SOURCE_TYPE` | `auto` | `auto`, `csv`, `json` |
| `PROPERTY_MIN_CONFIDENCE` | `0.35` | 抽出しきい値 |
| `NOTION_VERSION` | `2026-03-11` | Notion API version |

## 4. 初回テスト

GitHub Actionsの `Collect community property posts to Notion` を開き、次の値で手動実行します。

- `source_path`: `samples/community_posts.csv`
- `dry_run`: `true`
- `notion_sync`: `false`

完了後、artifact `property-listings` を確認します。

## 5. 本番同期

抽出内容に問題がなければ、手動実行で次の値にします。

- `dry_run`: `false`
- `notion_sync`: `true`

定期実行でも登録したい場合はVariablesを次のようにします。

```text
NOTION_SYNC=true
PROPERTY_SYNC_DRY_RUN=false
```

## 6. Facebookグループ投稿の取り込みについて

Metaは2024年4月22日以降、Facebook Groups APIの広範な第三者アクセスを廃止しています。そのため、このリポジトリはFacebookグループ画面のスクレイピングを実装していません。

現実的な取り込み方法は以下です。

- コミュニティ管理者または投稿者が許可したCSV/JSONエクスポート
- メール通知を自分の受信箱から構造化する仕組み
- フォーム投稿をGoogle SheetsやCSVに集める運用
- Meta側で明示的に承認されたAPIアクセスがある場合のみ `facebook-graph` source

## 7. トラブルシュート

| 症状 | 原因 | 対応 |
|---|---|---|
| Notion 401 | APIキー不正 | `NOTION_API_KEY` を再確認 |
| Notion 403 | Capabilities不足 | IntegrationでRead/Insert contentを有効化 |
| Notion 404 | Data Source未共有またはID違い | Data SourceにIntegrationをAdd connections |
| ページが重複する | `外部ID` 列がない | `外部ID` Rich text列を追加 |
| 物件が抽出されない | confidenceが低い | `PROPERTY_MIN_CONFIDENCE` を下げる、CSV本文を詳しくする |
