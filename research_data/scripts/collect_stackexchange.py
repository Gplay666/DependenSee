#!/usr/bin/env python3
"""Collect candidate Q&A posts from Ask Ubuntu and Unix & Linux Stack Exchange."""
import html
import json
import re
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "raw" / "stackexchange"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    "unused packages",
    "remove unused dependencies",
    "orphaned packages",
    "autoremove",
    "dependency tree",
    "dependency graph",
    "visualize dependencies",
    "reverse dependencies",
    "disk space packages",
    "clean up packages",
    "remove packages safely",
    "broken dependencies",
    "package manager gui",
    "find unused libraries",
    "apt purge",
    "installed packages size",
    "snap disk space",
    "flatpak unused runtimes",
    "remote server packages",
    "aptitude why",
    "deborphan",
    "dpkg dependencies",
]

SITES = ["askubuntu", "unix"]
BASE = "https://api.stackexchange.com/2.3/search/advanced"
session = requests.Session()


def clean(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def main():
    seen = set()
    posts = []
    for site in SITES:
        for q in QUERIES:
            slug = f"{site}__{q}".replace(" ", "_")
            path = OUT / f"{slug}.json"
            if path.exists():
                items = json.loads(path.read_text())
            else:
                params = {
                    "order": "desc",
                    "sort": "relevance",
                    "q": q,
                    "site": site,
                    "fromdate": 1577836800,
                    "pagesize": 40,
                    "filter": "withbody",
                }
                try:
                    r = session.get(BASE, params=params, timeout=30)
                    data = r.json()
                    items = data.get("items", [])
                    if "error_message" in data:
                        print(site, q, "ERROR", data["error_message"], flush=True)
                    path.write_text(json.dumps(items, ensure_ascii=False))
                    time.sleep(0.4)
                except Exception as exc:
                    print(site, q, "ERR", exc, flush=True)
                    continue
            print(f"{site} :: {q} -> {len(items)}", flush=True)
            for it in items:
                key = (site, it["question_id"])
                if key in seen:
                    continue
                seen.add(key)
                posts.append({
                    "site": site,
                    "question_id": it["question_id"],
                    "title": clean(it["title"]),
                    "url": it["link"],
                    "date": time.strftime("%Y-%m-%d", time.gmtime(it["creation_date"])),
                    "creation_date": it["creation_date"],
                    "score": it.get("score"),
                    "answers": it.get("answer_count"),
                    "views": it.get("view_count"),
                    "tags": it.get("tags", []),
                    "body": clean(it.get("body", ""))[:4000],
                    "is_answered": it.get("is_answered"),
                })

    posts.sort(key=lambda p: p["creation_date"], reverse=True)
    (OUT / "_all_candidates.json").write_text(json.dumps(posts, ensure_ascii=False))
    print("TOTAL unique:", len(posts))


if __name__ == "__main__":
    main()
