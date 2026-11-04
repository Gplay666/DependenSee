#!/usr/bin/env python3
"""Print stored Stack Exchange candidates in full-ish form for manual review."""
import json
import sys
from pathlib import Path

posts = json.loads((Path(__file__).resolve().parents[1] / "raw" / "stackexchange" / "_all_candidates.json").read_text())
by_id = {str(p["question_id"]): p for p in posts}
ids = sys.argv[1:]
for qid in ids:
    p = by_id.get(qid)
    if not p:
        print(f"### {qid} NOT FOUND\n")
        continue
    print(f"### {qid} | {p['date']} | {p['site']} | score={p['score']} answers={p['answers']} views={p['views']}")
    print(f"{p['title']}\n{p['url']}")
    print(f"TAGS: {', '.join(p['tags'])}")
    print(f"BODY: {p['body'][:1200]}\n")
