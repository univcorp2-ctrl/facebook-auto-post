from __future__ import annotations

import argparse
import json
import sys

from .client import FacebookAPIError, FacebookPageClient
from .config import AppConfig
from .content import resolve_post_content


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Post content to a Facebook Page.")
    parser.add_argument("--dry-run", action="store_true", help="Print the post payload without publishing")
    parser.add_argument("--posts-file", help="Path to posts JSON file")
    parser.add_argument("--post-index", type=int, help="Select a specific post index from the posts file")
    parser.add_argument("--message", help="One-off message override")
    parser.add_argument("--link", help="Optional link for the one-off message")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig.from_env()

    dry_run = args.dry_run or config.dry_run
    posts_file = args.posts_file or config.posts_file
    post_index = args.post_index if args.post_index is not None else config.post_index
    post_text = args.message if args.message is not None else config.post_text
    post_link = args.link if args.link is not None else config.post_link

    try:
        content = resolve_post_content(
            post_text=post_text,
            post_link=post_link,
            posts_file=posts_file,
            post_index=post_index,
        )

        if dry_run:
            print(json.dumps({"dry_run": True, "post": content.as_payload()}, ensure_ascii=False, indent=2))
            return 0

        if not config.page_id or not config.page_access_token:
            print(
                "FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN are required unless --dry-run or DRY_RUN=true is set.",
                file=sys.stderr,
            )
            return 2

        client = FacebookPageClient(graph_version=config.graph_version)
        result = client.publish_feed_post(
            page_id=config.page_id,
            page_access_token=config.page_access_token,
            message=content.message,
            link=content.link,
        )
        print(json.dumps({"published": True, "result": result}, ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, ValueError, FacebookAPIError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
