#!/usr/bin/env python3
"""Rank already-collected Stack Exchange candidates for manual review."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "raw" / "stackexchange"
posts = json.loads((BASE / "_all_candidates.json").read_text())

STRONG = {
    "unused": 6, "orphan": 6, "orphaned": 6, "autoremove": 5,
    "dependency": 3, "dependencies": 3, "graph": 5, "visualize": 5,
    "visualization": 5, "tree": 3, "reverse": 3, "disk space": 4,
    "cleanup": 4, "clean up": 4, "safely": 3, "safe": 2, "size": 2,
    "broken": 2, "remote": 3, "free space": 3, "leftover": 4,
    "unneeded": 5, "remove": 1, "purge": 3, "deborphan": 6, "why": 2,
}

def score(p):
    title = p["title"].lower()
    body = p["body"].lower()
    s = 0
    hits = []
    for kw, w in STRONG.items():
        if kw in title:
            s += w * 2
            hits.append(kw)
        if kw in body:
            s += w
    # penalise generic install/config questions
    for bad in ["install", "installer", "cannot boot", "wifi", "nvidia", "sound", "grub"]:
        if bad in title:
            s -= 4
    return s, hits

rows = []
for p in posts:
    s, hits = score(p)
    rows.append((s, p, hits))
rows.sort(key=lambda x: (-x[0], -x[1]["score"], x[1]["creation_date"]))

with open(BASE / "_shortlist.txt", "w") as f:
    for i, (s, p, hits) in enumerate(rows[:200], 1):
        f.write(f"{i:3d} s={s:3d} score={p['score']:4d} ans={p['answers']:2d} {p['date']} {p['site']:9s} {p['title'][:110]}\n")
        f.write(f"      {p['url']}\n")
print("written", len(rows))
