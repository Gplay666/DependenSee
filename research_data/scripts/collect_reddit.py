#!/usr/bin/env python3
"""Collect candidate Reddit posts from the Arctic Shift archive API.

The archive is a third-party mirror of Reddit. Scores/comment counts are
snapshots taken by the archive, not live Reddit values.
"""
import json
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "raw" / "reddit"
OUT.mkdir(parents=True, exist_ok=True)

SUBREDDITS = [
    "linux",
    "linuxquestions",
    "linux4noobs",
    "debian",
    "Ubuntu",
    "archlinux",
    "fedora",
    "linuxmint",
]

QUERIES = [
    "unused packages",
    "unused dependencies",
    "orphaned packages",
    "dependency tree",
    "dependency graph",
    "autoremove",
]

EXTRA = {
    "linux": ["remove packages safely", "disk space packages", "visualize dependencies"],
    "linuxquestions": ["remove packages safely", "disk space", "broken dependencies"],
    "archlinux": ["pacman orphans", "remove dependencies"],
    "Ubuntu": ["disk space packages", "remove packages"],
    "debian": ["disk space packages", "remove packages"],
}

BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
session = requests.Session()
session.headers["User-Agent"] = "dependensee-research/1.0 (academic data collection)"


def fetch(sub, query):
    params = {
        "subreddit": sub,
        "query": query,
        "limit": 100,
        "after": "2020-01-01",
        "before": "2026-11-04",
    }
    for attempt in range(4):
        try:
            r = session.get(BASE, params=params, timeout=60)
            if r.status_code == 200:
                return r.json().get("data", [])
            print(f"  HTTP {r.status_code}: {r.text[:120]}", flush=True)
        except Exception as exc:  # network hiccups
            print(f"  ERR {exc}", flush=True)
        time.sleep(8 * (attempt + 1))
    return None


def main():
    seen = set()
    all_posts = []
    jobs = [(s, q) for s in SUBREDDITS for q in QUERIES]
    for s, qs in EXTRA.items():
        jobs += [(s, q) for q in qs]

    for i, (sub, query) in enumerate(jobs, 1):
        slug = f"{sub}__{query}".replace(" ", "_").replace("/", "_")
        path = OUT / f"{slug}.json"
        if path.exists():
            data = json.loads(path.read_text())
            print(f"[{i}/{len(jobs)}] cached {sub} :: {query} -> {len(data)}", flush=True)
        else:
            data = fetch(sub, query)
            if data is None:
                print(f"[{i}/{len(jobs)}] FAILED {sub} :: {query}", flush=True)
                time.sleep(10)
                continue
            path.write_text(json.dumps(data, ensure_ascii=False))
            print(f"[{i}/{len(jobs)}] {sub} :: {query} -> {len(data)}", flush=True)
            time.sleep(4)
        for p in data:
            if p["id"] not in seen:
                seen.add(p["id"])
                all_posts.append(p)

    (OUT / "_all_candidates.json").write_text(json.dumps(all_posts, ensure_ascii=False))
    print(f"TOTAL unique: {len(all_posts)}")


if __name__ == "__main__":
    main()
