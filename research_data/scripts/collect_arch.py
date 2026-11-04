#!/usr/bin/env python3
"""Collect candidate Arch Linux BBS topics (public HTML)."""
import html
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parents[1] / "raw" / "arch"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    "unused packages",
    "unused dependencies",
    "orphaned packages",
    "dependency tree",
    "dependency graph",
    "autoremove",
    "remove packages safely",
    "disk space packages",
    "clean up packages",
    "pacman -Qtd",
    "reverse dependencies",
    "visualize dependencies",
    "unneeded packages",
    "remove dependencies",
]

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) dependensee-research/1.0"


def clean(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def parse_search(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    out = []
    for row in soup.select("table tbody tr"):
        link = row.select_one('a[href^="viewtopic.php?id="]')
        if not link:
            continue
        forum = row.select_one("td.tc2")
        replies = row.select_one("td.tc3")
        last = row.select_one("td.tcr a[href*='pid=']")
        out.append({
            "topic_id": int(re.search(r"id=(\d+)", link["href"]).group(1)),
            "title": clean(link.get_text()),
            "forum": clean(forum.get_text()) if forum else None,
            "replies": int(clean(replies.get_text()).replace(",", "")) if replies and clean(replies.get_text()).isdigit() or (replies and clean(replies.get_text()).replace(",", "").isdigit()) else None,
            "last_post": clean(last.get_text()) if last else None,
        })
    return out


def parse_topic(html_text, tid):
    soup = BeautifulSoup(html_text, "lxml")
    first = soup.select_one("div.blockpost.firstpost")
    if not first:
        return None
    h2 = first.select_one("h2 a")
    h3 = first.select_one("h3")
    body = first.select_one("div.postmsg")
    header = clean(first.get_text(" "))
    m = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", header)
    return {
        "topic_id": tid,
        "date": m.group(1) if m else None,
        "created_at": f"{m.group(1)} {m.group(2)}" if m else None,
        "title": clean(h3.get_text()) if h3 else None,
        "url": f"https://bbs.archlinux.org/viewtopic.php?id={tid}",
        "body": clean(body.get_text(" "))[:5000] if body else "",
        "posts_on_page": len(soup.select("div.blockpost")),
    }


def main():
    topics = {}
    for q in QUERIES:
        slug = "search__" + q.replace(" ", "_").replace("-", "")
        path = OUT / f"{slug}.html"
        if path.exists():
            html_text = path.read_text(errors="ignore")
        else:
            r = session.get("https://bbs.archlinux.org/search.php", params={
                "action": "search", "keywords": q, "sort_by": 0,
                "sort_dir": "DESC", "show_as": "topics",
            }, timeout=40)
            html_text = r.text
            path.write_text(html_text)
            time.sleep(1)
        found = parse_search(html_text)
        print(q, "->", len(found), flush=True)
        for t in found:
            topics.setdefault(t["topic_id"], t)
            topics[t["topic_id"]].setdefault("queries", []).append(q)

    rows = []
    for i, (tid, t) in enumerate(topics.items(), 1):
        path = OUT / f"topic_{tid}.json"
        if path.exists():
            d = json.loads(path.read_text())
        else:
            try:
                r = session.get(f"https://bbs.archlinux.org/viewtopic.php?id={tid}", timeout=40)
                if r.status_code != 200:
                    continue
                d = parse_topic(r.text, tid) or {}
                if d:
                    d["replies"] = t.get("replies")
                    d["forum"] = t.get("forum")
                    d["last_post"] = t.get("last_post")
                    path.write_text(json.dumps(d, ensure_ascii=False))
                time.sleep(0.6)
            except Exception as exc:
                print("topic", tid, "ERR", exc, flush=True)
                continue
        if d:
            d["queries"] = t.get("queries", [])
            rows.append(d)
        if i % 25 == 0:
            print("fetched", i, "/", len(topics), flush=True)

    rows.sort(key=lambda r: r.get("date") or "", reverse=True)
    (OUT / "_all_candidates.json").write_text(json.dumps(rows, ensure_ascii=False))
    print("TOTAL unique topics:", len(rows))


if __name__ == "__main__":
    main()
