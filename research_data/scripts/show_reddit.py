#!/usr/bin/env python3
"""Consolidate Reddit archive candidates and print selected posts for review."""
import datetime
import glob
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "raw" / "reddit"
posts = {}
for f in glob.glob(str(BASE / "*.json")):
    if f.endswith("_all_candidates.json") or f.endswith("_candidates.json"):
        continue
    try:
        data = json.loads(Path(f).read_text())
    except Exception:
        continue
    for p in data:
        posts[p["id"]] = p

alive = []
for p in posts.values():
    if p.get("selftext") in ("[removed]", "[deleted]"):
        continue
    if (p.get("_meta") or {}).get("removal_type"):
        continue
    p["date"] = datetime.datetime.fromtimestamp(p["created_utc"], datetime.UTC).strftime("%Y-%m-%d")
    p["url"] = "https://www.reddit.com" + p["permalink"]
    p["body"] = (p.get("selftext") or "").strip()
    alive.append(p)
alive.sort(key=lambda p: p["created_utc"], reverse=True)
(BASE / "_candidates.json").write_text(json.dumps(alive, ensure_ascii=False))
print(f"# consolidated {len(alive)} posts", file=sys.stderr)

for arg in sys.argv[1:]:
    matches = [p for p in alive if arg.lower() in p["title"].lower() or p["id"] == arg]
    for p in matches[:4]:
        print(f"### {p['id']} | {p['date']} | r/{p['subreddit']} | score={p['score']} comments={p['num_comments']}")
        print(p["title"])
        print(p["url"])
        print(f"BODY: {p['body'][:1800]}\n")
