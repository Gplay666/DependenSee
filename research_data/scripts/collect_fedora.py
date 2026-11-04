#!/usr/bin/env python3
"""Collect candidate Fedora Discussion topics via the public Discourse API."""
import html
import json
import re
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "raw" / "fedora"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    "unused packages",
    "unused dependencies",
    "orphaned packages",
    "dependency tree",
    "dependency graph",
    "visualize dependencies",
    "autoremove",
    "remove packages safely",
    "disk space packages",
    "clean up packages",
    "reverse dependencies",
    "dnf remove dependencies",
    "flatpak unused",
    "package cleanup",
]

session = requests.Session()
session.headers["User-Agent"] = "dependensee-research/1.0"


def clean(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def main():
    topics = {}
    for q in QUERIES:
        slug = "search__" + q.replace(" ", "_")
        path = OUT / f"{slug}.json"
        if path.exists():
            data = json.loads(path.read_text())
        else:
            r = session.get("https://discussion.fedoraproject.org/search.json", params={"q": q}, timeout=40)
            data = r.json()
            path.write_text(json.dumps(data, ensure_ascii=False))
            time.sleep(1)
        print(q, "->", len(data.get("topics", [])), flush=True)
        for t in data.get("topics", []):
            topics.setdefault(t["id"], t)

    details = {}
    for i, tid in enumerate(topics, 1):
        path = OUT / f"topic_{tid}.json"
        if path.exists():
            details[tid] = json.loads(path.read_text())
        else:
            try:
                r = session.get(f"https://discussion.fedoraproject.org/t/{tid}.json", timeout=40)
                if r.status_code != 200:
                    print("topic", tid, "HTTP", r.status_code, flush=True)
                    continue
                details[tid] = r.json()
                path.write_text(json.dumps(details[tid], ensure_ascii=False))
                time.sleep(0.7)
            except Exception as exc:
                print("topic", tid, "ERR", exc, flush=True)
        if i % 25 == 0:
            print("fetched", i, "/", len(topics), flush=True)

    rows = []
    for tid, d in details.items():
        posts = d.get("post_stream", {}).get("posts", [])
        first = next((p for p in posts if p.get("post_number") == 1), posts[0] if posts else None)
        if not first:
            continue
        rows.append({
            "topic_id": tid,
            "title": d.get("title"),
            "url": f"https://discussion.fedoraproject.org/t/{d.get('slug', tid)}/{tid}",
            "date": (first.get("created_at") or "")[:10],
            "created_at": first.get("created_at"),
            "posts_count": d.get("posts_count"),
            "reply_count": d.get("reply_count"),
            "views": d.get("views"),
            "like_count": d.get("like_count"),
            "tags": [t if isinstance(t, str) else t.get("name") for t in d.get("tags", [])],
            "category_id": d.get("category_id"),
            "body": clean(first.get("cooked", ""))[:4000],
        })
    rows.sort(key=lambda r: r["created_at"] or "", reverse=True)
    (OUT / "_all_candidates.json").write_text(json.dumps(rows, ensure_ascii=False))
    print("TOTAL unique topics:", len(rows))


if __name__ == "__main__":
    main()
