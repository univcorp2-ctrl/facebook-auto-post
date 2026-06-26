# CODEX

## Mission

This repository automates two workflows:

1. Facebook Page scheduled posting through the official Graph API Page feed endpoint.
2. Community property listing aggregation into Notion through a compliant import pipeline.

## Guardrails

- Do not add browser scraping, credential sharing, or private Facebook group bypass automation.
- Facebook group content must come from a lawful/approved source: CSV, JSON, a user-owned export, webhook, email parser, or an explicitly approved API integration.
- Secrets belong in GitHub Actions Secrets or local `.env`; never commit real tokens.
- Notion sync should target `NOTION_DATA_SOURCE_ID` with `Notion-Version: 2026-03-11`.

## Local commands

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
property-notion-sync --dry-run --source samples/community_posts.csv
```

## Production requirements

- `NOTION_API_KEY`
- `NOTION_DATA_SOURCE_ID`
- A source file or approved ingestion source containing community posts
- Repository variable `NOTION_SYNC=true` and `PROPERTY_SYNC_DRY_RUN=false` only after dry-run output has been checked
