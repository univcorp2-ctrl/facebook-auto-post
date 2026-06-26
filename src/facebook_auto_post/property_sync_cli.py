from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .config import parse_bool
from .notion_client import NotionConfig, NotionPropertyClient
from .property_sources import FacebookGroupFeedSource, SourceError, load_posts_from_file
from .property_sync import PropertySyncer, SyncOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect community property posts and optionally sync them to Notion."
    )
    parser.add_argument(
        "--source",
        default=os.getenv("PROPERTY_SOURCE_PATH", "samples/community_posts.csv"),
        help="CSV/JSON source path. Default: samples/community_posts.csv",
    )
    parser.add_argument(
        "--source-type",
        choices=["auto", "csv", "json", "facebook-graph"],
        default=os.getenv("PROPERTY_SOURCE_TYPE", "auto"),
    )
    parser.add_argument("--output", default=os.getenv("PROPERTY_OUTPUT_PATH", "outputs/property-listings.json"))
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--notion-sync", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=float(os.getenv("PROPERTY_MIN_CONFIDENCE", "0.35")),
    )
    parser.add_argument("--include-low-confidence", action="store_true")
    parser.add_argument("--facebook-group-ids", help="Comma-separated group IDs for approved Graph API use")
    parser.add_argument("--facebook-limit", type=int, default=int(os.getenv("FACEBOOK_GROUP_LIMIT", "25")))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    notion_sync = (
        args.notion_sync
        if args.notion_sync is not None
        else parse_bool(os.getenv("NOTION_SYNC"), default=False)
    )
    dry_run = (
        args.dry_run
        if args.dry_run is not None
        else parse_bool(os.getenv("PROPERTY_SYNC_DRY_RUN"), default=not notion_sync)
    )

    try:
        posts = load_posts(args)
        notion_client = None
        if notion_sync and not dry_run:
            notion_client = NotionPropertyClient(NotionConfig.from_env())
        syncer = PropertySyncer(
            notion_client=notion_client,
            options=SyncOptions(
                dry_run=dry_run,
                min_confidence=args.min_confidence,
                include_low_confidence=args.include_low_confidence,
            ),
        )
        report = syncer.run(posts)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return 1 if report.errors and not dry_run else 0
    except (FileNotFoundError, ValueError, SourceError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def load_posts(args: argparse.Namespace):
    if args.source_type == "facebook-graph":
        group_ids = _split_csv(args.facebook_group_ids or os.getenv("FACEBOOK_GROUP_IDS", ""))
        source = FacebookGroupFeedSource(
            group_ids=group_ids,
            access_token=os.getenv("FB_USER_ACCESS_TOKEN", ""),
            graph_version=os.getenv("FB_GRAPH_VERSION", "v25.0"),
            limit=args.facebook_limit,
        )
        return source.load()
    return load_posts_from_file(args.source, source_type=args.source_type)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
