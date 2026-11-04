#!/usr/bin/env python3
"""Print Arch BBS topic candidates by title substring."""
import glob
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "raw" / "arch"
rows = []
for f in glob.glob(str(BASE / "topic_*.json")):
    try:
        d = json.loads(Path(f).read_text())
    except Exception:
        continue
    rows.append(d)

for arg in sys.argv[1:]:
    matches = [r for r in rows if arg.lower() in (r.get("title") or "").lower()]
    for r in matches[:5]:
        print(f"### {r.get('topic_id')} | {r.get('date')} | replies={r.get('replies')}")
        print(r.get("title"))
        print(r.get("url"))
        print(f"BODY: {(r.get('body') or '')[:1600]}\n")
