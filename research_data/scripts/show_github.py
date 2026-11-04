#!/usr/bin/env python3
"""Print stored GitHub candidates by title substring or issue number."""
import json
import sys
from pathlib import Path

rows = json.loads((Path(__file__).resolve().parents[1] / "raw" / "github" / "_all_candidates.json").read_text())
for arg in sys.argv[1:]:
    matches = [r for r in rows if arg.lower() in r["title"].lower() or arg == str(r["number"])]
    for r in matches[:4]:
        print(f"### {r['repo']}#{r['number']} | {r['date']} | comments={r['comments']} reactions={r['reactions']} | {r['state']}")
        print(r["title"])
        print(r["url"])
        print(f"BODY: {r['body'][:1800]}\n")
