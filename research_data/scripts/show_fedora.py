#!/usr/bin/env python3
"""Print Fedora Discussion candidate bodies by topic id or title substring."""
import json
import sys
from pathlib import Path

rows = json.loads((Path(__file__).resolve().parents[1] / "raw" / "fedora" / "_all_candidates.json").read_text())
for arg in sys.argv[1:]:
    matches = [r for r in rows if str(r["topic_id"]) == arg or arg.lower() in (r["title"] or "").lower()]
    for r in matches[:3]:
        print(f"### {r['topic_id']} | {r['date']} | posts={r['posts_count']} views={r['views']}")
        print(r["title"])
        print(r["url"])
        print(f"BODY: {r['body'][:1600]}\n")
