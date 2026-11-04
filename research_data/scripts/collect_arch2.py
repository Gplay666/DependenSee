#!/usr/bin/env python3
"""Arch BBS search, respecting the 60-second search flood limit.

Uses title-only search to reduce noise, waits 65 s between queries, then
fetches matching topic pages (topic pages are not rate-limited).
"""
import html
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parents[1] / "raw" / "arch"
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = ["unused", "orphan", "dependency", "autoremove", "disk space", "clean"]

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) dependensee-research/1.0"


def clean(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def parse_search(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    out = []
    for row in soup.select("div#vf table tbody tr"):
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
            "replies": int(clean(replies.get_text()).replace(",", "")) if replies and clean(replies.get_text()).replace(",", "").isdigit() else None,
            "last_post": clean(last.get_text()) if last else None,
        })
    return out


def parse_topic(html_text, tid):
    soup = BeautifulSoup(html_text, "lxml")
    first = soup.select_one("div.blockpost.firstpost")
    if not first:
        return None
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
    }


def main():
    topics = {}
    for i, q in enumerate(QUERIES):
        if i:
            time.sleep(65)
        r = session.get("https://bbs.archlinux.org/search.php", params={
            "action": "search", "keywords": q, "search_in": 1,
            "sort_by": 0, "sort_dir": "DESC", "show_as": "topics",
        }, timeout=40)
        found = parse_search(r.text)
        print(q, "->", len(found), flush=True)
        for t in found:
            entry = topics.setdefault(t["topic_id"], t)
            entry.setdefault("queries", []).append(q)

    rows = []
    for i, (tid, t) in enumerate(topics.items(), 1):
        path = OUT / f"topic_{tid}.json"
        if path.exists():
            d = json.loads(path.read_text())
        else:
            r = session.get(f"https://bbs.archlinux.org/viewtopic.php?id={tid}", timeout=40)
            if r.status_code != 200:
                continue
            d = parse_topic(r.text, tid) or {}
            if d:
                d["replies"] = t.get("replies")
                d["forum"] = t.get("forum")
                d["last_post"] = t.get("last_post")
                path.write_text(json.dumps(d, ensure_ascii=False))
            time.sleep(0.5)
        if d:
            d["queries"] = t.get("queries", [])
            rows.append(d)
        if i % 20 == 0:
            print("fetched", i, "/", len(topics), flush=True)

    rows.sort(key=lambda r: r.get("date") or "", reverse=True)
    (OUT / "_relevant_candidates.json").write_text(json.dumps(rows, ensure_ascii=False))
    print("TOTAL:", len(rows))


if __name__ == "__main__":
    main()
