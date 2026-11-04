#!/usr/bin/env python3
"""Join curated records with collected metadata, validate evidence, export CSV/JSON."""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "raw"
OUT_CSV = BASE / "discussions.csv"
OUT_JSON = BASE / "discussions.json"

sys.path.insert(0, str(BASE / "scripts"))
from curated_reddit import REDDIT  # noqa: E402
from curated_se import STACKEXCHANGE  # noqa: E402
from curated_fedora import FEDORA  # noqa: E402
from curated_github import GITHUB  # noqa: E402

try:
    from curated_arch import ARCH  # noqa: E402
except ImportError:
    ARCH = []

FIELDS = [
    "id", "source", "url", "title", "date", "distro", "problem_category",
    "problem_description", "user_request", "mentions_visualization",
    "mentions_dependencies", "mentions_cleanup", "mentions_disk_space",
    "mentions_safety", "score", "comments_count", "evidence",
]

SE_NAMES = {
    "askubuntu": "Ask Ubuntu",
    "unix": "Unix & Linux Stack Exchange",
}


def normalize(text: str) -> str:
    text = html.unescape(text or "")
    text = (text.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u00a0", " "))
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def load(name: str):
    path = RAW / name
    return json.loads(path.read_text())


def main() -> int:
    reddit = {p["id"]: p for p in load("reddit/_candidates.json")}
    se = {str(p["question_id"]): p for p in load("stackexchange/_all_candidates.json")}
    fedora = {str(p["topic_id"]): p for p in load("fedora/_all_candidates.json")}
    github = {f"{p['repo']}#{p['number']}": p for p in load("github/_all_candidates.json")}
    arch = {}
    arch_path = RAW / "arch/_relevant_candidates.json"
    if arch_path.exists():
        arch = {str(p["topic_id"]): p for p in json.loads(arch_path.read_text())}

    records = []
    failures = []

    def add(item, meta, source_name, score, comments):
        title = meta.get("title") or ""
        body = meta.get("body") or meta.get("selftext") or ""
        haystack = normalize(title + "\n" + body)
        if normalize(item["evidence"]) not in haystack:
            failures.append((source_name, item["key"], item["evidence"],
                             title, normalize(body)[:300]))
        records.append({
            "source": source_name,
            "url": meta["url"],
            "title": title,
            "date": meta["date"],
            "distro": item["distro"],
            "problem_category": item["category"],
            "problem_description": item["desc"],
            "user_request": item["request"],
            "mentions_visualization": bool(item["vis"]),
            "mentions_dependencies": bool(item["deps"]),
            "mentions_cleanup": bool(item["cleanup"]),
            "mentions_disk_space": bool(item["disk"]),
            "mentions_safety": bool(item["safety"]),
            "score": score,
            "comments_count": comments,
            "evidence": item["evidence"],
        })

    for item in REDDIT:
        meta = reddit.get(item["key"])
        if not meta:
            failures.append(("Reddit", item["key"], "MISSING METADATA", "", ""))
            continue
        add(item, meta, f"Reddit (r/{meta['subreddit']})",
            meta.get("score"), meta.get("num_comments"))

    for item in STACKEXCHANGE:
        meta = se.get(str(item["key"]))
        if not meta:
            failures.append(("Stack Exchange", item["key"], "MISSING METADATA", "", ""))
            continue
        add(item, meta, SE_NAMES.get(meta["site"], meta["site"]),
            meta.get("score"), meta.get("answers"))

    for item in FEDORA:
        meta = fedora.get(str(item["key"]))
        if not meta:
            failures.append(("Fedora Discussion", item["key"], "MISSING METADATA", "", ""))
            continue
        add(item, meta, "Fedora Discussion", None,
            max((meta.get("posts_count") or 1) - 1, 0))

    for item in GITHUB:
        meta = github.get(item["key"])
        if not meta:
            failures.append(("GitHub", item["key"], "MISSING METADATA", "", ""))
            continue
        add(item, meta, f"GitHub ({meta['repo']})", None, meta.get("comments"))

    for item in ARCH:
        meta = arch.get(str(item["key"]))
        if not meta:
            failures.append(("Arch Linux Forums", item["key"], "MISSING METADATA", "", ""))
            continue
        add(item, meta, "Arch Linux Forums", None, meta.get("replies"))

    if failures:
        print(f"VALIDATION FAILED: {len(failures)} issue(s)")
        for src, key, ev, title, body in failures:
            print(f"- {src} / {key}: {title[:80]}")
            print(f"  evidence: {ev!r}")
            print(f"  body: {body[:200]!r}")
        return 1

    records.sort(key=lambda r: (r["date"], r["source"], r["url"]), reverse=True)
    for i, rec in enumerate(records, 1):
        rec["id"] = f"DS-{i:03d}"
    records = [{k: rec[k] for k in FIELDS} for rec in records]

    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            for key in ("mentions_visualization", "mentions_dependencies",
                        "mentions_cleanup", "mentions_disk_space", "mentions_safety"):
                row[key] = "true" if row[key] else "false"
            for key in ("distro", "score", "comments_count"):
                if row[key] is None:
                    row[key] = ""
            writer.writerow(row)

    print(f"OK: {len(records)} records -> {OUT_CSV.name}, {OUT_JSON.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
