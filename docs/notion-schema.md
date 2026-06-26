# Notion Schema

推奨Data Source名: `コミュニティ物件情報`

| Property | Type | Required | Notes |
|---|---|---:|---|
| 物件名 | Title | yes | ページタイトル。存在するTitle列なら別名でも自動検出します |
| 外部ID | Rich text | yes | 重複判定。`property-...` の安定ID |
| コミュニティ | Rich text | no | 投稿元 |
| 投稿者 | Rich text | no | 投稿者名。取得元に含まれる場合のみ |
| 投稿日 | Date | no | ISO文字列をDateに登録 |
| 投稿URL | URL | no | 投稿のpermalink |
| 家賃 | Number | no | 円単位 |
| 間取り | Rich text | no | 1R, 1K, 1LDKなど |
| 最寄駅 | Rich text | no | `新宿駅` など |
| 徒歩分 | Number | no | 駅徒歩分 |
| 面積㎡ | Number | no | 専有面積 |
| 住所 | Rich text | no | 抽出された住所 |
| タグ | Multi-select | no | ペット可、即入居など |
| 本文 | Rich text | no | 投稿本文。長文はページ本文ブロックにも保存 |
| 信頼度 | Number | no | 0.0〜1.0 |

## Flexible mapping

コードはData Source schemaを先に読み、存在する列だけに書き込みます。例えば `家賃` 列がなくてもページ作成は続行されます。ただし重複排除には `外部ID` が必要です。

## Legacy database mode

古いNotion API運用では `NOTION_DATABASE_ID` も使えますが、2026-03-11ではData Source APIが推奨です。新規運用は `NOTION_DATA_SOURCE_ID` を使ってください。
