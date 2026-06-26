from __future__ import annotations

from datetime import date
import json

from facebook_auto_post.content import load_posts, resolve_post_content, select_post


def test_load_posts_from_object(tmp_path):
    posts_file = tmp_path / "posts.json"
    posts_file.write_text(
        json.dumps({"posts": [{"message": " hello ", "link": " https://example.com "}]}),
        encoding="utf-8",
    )

    posts = load_posts(posts_file)

    assert len(posts) == 1
    assert posts[0].message == "hello"
    assert posts[0].link == "https://example.com"


def test_select_post_uses_explicit_index_modulo():
    posts = resolve_posts(["a", "b", "c"])
    selected = select_post(posts, index=4)
    assert selected.message == "b"


def test_select_post_uses_date_when_index_missing():
    posts = resolve_posts(["a", "b", "c"])
    current = date(2026, 5, 12)
    selected = select_post(posts, today=current)
    assert selected == posts[current.toordinal() % len(posts)]


def test_resolve_post_content_prefers_env_override(tmp_path):
    missing_file = tmp_path / "missing.json"

    selected = resolve_post_content(
        post_text="manual post",
        post_link="https://example.com/manual",
        posts_file=missing_file,
    )

    assert selected.message == "manual post"
    assert selected.link == "https://example.com/manual"


def resolve_posts(messages: list[str]):
    return [resolve_post_content(post_text=message, post_link=None, posts_file="unused") for message in messages]
