#!/usr/bin/env python3
"""Collect candidate GitHub issues/feature requests about package cleanup,
dependency visibility, disk space and safe package removal."""
import json
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "raw" / "github"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    '"unused packages" linux in:title,body type:issue',
    '"unused dependencies" apt in:title,body type:issue',
    '"orphaned packages" in:title,body type:issue',
    '"dependency graph" package manager in:title,body type:issue',
    '"visualize dependencies" in:title,body type:issue',
    '"reverse dependencies" in:title,body type:issue',
    '"remove unused packages" in:title,body type:issue',
    '"autoremove" package in:title,body type:issue',
    '"dependency tree" apt in:title,body type:issue',
    '"disk space" packages linux in:title,body type:issue',
    '"package cleanup" linux in:title,body type:issue',
    '"unused" "package manager" linux in:title,body type:issue',
]

REPO_QUERIES = [
    "repo:debian/apt unused in:title,body type:issue",
    "repo:archlinux/pacman orphan in:title,body type:issue",
    "repo:archlinux/pacman dependency in:title,body type:issue",
    "repo:rpm-software-management/dnf5 unused in:title,body type:issue",
    "repo:volian/nala autoremove in:title,body type:issue",
    "repo:oguzhaninan/Stacer package in:title,body type:issue",
    "repo:bleachbit/bleachbit package in:title,body type:issue",
    "repo:Jguer/yay orphan in:title,body type:issue",
    "repo:Morganamilo/paru orphan in:title,body type:issue",
]

BASE = "https://api.github.com/search/issues"
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github+json",
    "User-Agent": "dependensee-research",
})


def fetch(q):
    for attempt in range(3):
        r = session.get(BASE, params={"q": q, "per_page": 50, "sort": "relevance"}, timeout=40)
        if r.status_code == 200:
            return r.json()
        print("  HTTP", r.status_code, r.text[:150], flush=True)
        if r.status_code in (403, 429):
            time.sleep(30 * (attempt + 1))
        else:
            return None
    return None


def main():
    seen = set()
    posts = []
    for q in QUERIES + REPO_QUERIES:
        slug = q.replace(" ", "_").replace('"', "").replace(":", "-").replace("/", "-")[:120]
        path = OUT / f"{slug}.json"
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = fetch(q)
            if data is None:
                print("FAILED", q, flush=True)
                continue
            path.write_text(json.dumps(data, ensure_ascii=False))
            print(q, "->", data.get("total_count"), "total,", len(data.get("items", [])), "fetched", flush=True)
            time.sleep(7)
        for it in data.get("items", []):
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            posts.append({
                "id": it["id"],
                "number": it["number"],
                "repo": it["repository_url"].replace("https://api.github.com/repos/", ""),
                "title": it["title"],
                "url": it["html_url"],
                "date": it["created_at"][:10],
                "created_at": it["created_at"],
                "state": it["state"],
                "comments": it.get("comments"),
                "reactions": (it.get("reactions") or {}).get("total_count"),
                "labels": [l["name"] for l in it.get("labels", [])],
                "body": (it.get("body") or "")[:5000],
            })

    posts.sort(key=lambda p: p["created_at"], reverse=True)
    (OUT / "_all_candidates.json").write_text(json.dumps(posts, ensure_ascii=False))
    print("TOTAL unique:", len(posts))


if __name__ == "__main__":
    main()
