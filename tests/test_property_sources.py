from __future__ import annotations

import json

from facebook_auto_post.property_sources import load_posts_from_file


def test_load_posts_from_csv(tmp_path):
    path = tmp_path / "posts.csv"
    path.write_text(
        "source_id,source_name,author,message,created_time,permalink_url\n"
        "1,コミュニティA,佐藤,家賃8万円 1K 渋谷駅 徒歩5分,2026-06-25,https://example.com/1\n",
        encoding="utf-8",
    )

    posts = load_posts_from_file(path)

    assert len(posts) == 1
    assert posts[0].source_name == "コミュニティA"
    assert posts[0].message.startswith("家賃8万円")


def test_load_posts_from_json_object(tmp_path):
    path = tmp_path / "posts.json"
    path.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "id": "abc",
                        "group": "不動産グループ",
                        "text": "横浜駅 徒歩10分 2DK 賃料95000円",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    posts = load_posts_from_file(path)

    assert posts[0].source_id == "abc"
    assert posts[0].source_name == "不動産グループ"
