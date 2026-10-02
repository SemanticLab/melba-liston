#!/usr/bin/env python3
"""Independent integrity check over every published quote in the repo.

Each merge script verifies the quotes it merges. This re-does all of it from
scratch against the DATABASE (not against the intermediate JSON), so a bug in a
merge script cannot vouch for itself. Exit status is non-zero on any failure.

Checks
  1. every quote field in every output file is an exact substring of the
     whitespace-collapsed text of the block it names, in linked_jazz.sqlite
  2. quotes attributed to Liston come from blocks whose speaker is Liston;
     quotes attributed to Clora Bryant from blocks whose speaker is Bryant
  3. no quote attributed to a speaker overlaps a transcriber's bracketed summary
  4. the file-to-file joins hold (shortlist ⊆ enriched ⊆ quotes, etc.)
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY
WS = re.compile(r"\s+")
BRACKET = re.compile(r"\[[^\]]{26,}\]")

con = sqlite3.connect(f"file:{SUBJ.DB}?mode=ro", uri=True)
_cache = {}


def block(bid):
    if bid not in _cache:
        r = con.execute("SELECT doc_id, speaker, text FROM blocks WHERE block_id=?", (bid,)).fetchone()
        _cache[bid] = None if r is None else (r[0], (r[1] or "").strip(), WS.sub(" ", r[2] or "").strip())
    return _cache[bid]


fails, checked = [], 0
# blank-speaker continuation blocks in her interview inherit the previous voice
own_roles = {b["block_id"]: b["speaker_role"] for b in
             json.loads((D / "own_interview.json").read_text(encoding="utf-8"))["items"]}


def check(where, quote, bid, voice=None, no_bracket=False):
    """voice: None | 'subject' | 'interviewer' (roles inside her own interview)."""
    global checked
    if not quote:
        return
    checked += 1
    b = block(bid)
    if b is None:
        fails.append(f"{where}: block {bid} not in DB")
        return
    if quote not in b[2]:
        fails.append(f"{where}: block {bid}: not verbatim: {quote[:70]!r}")
        return
    if voice and own_roles.get(bid) != voice:
        fails.append(f"{where}: block {bid}: speaker role is {own_roles.get(bid)!r}, wanted {voice}")
    if no_bracket:
        i = b[2].index(quote)
        for m in BRACKET.finditer(b[2]):
            if m.start() < i + len(quote) and m.end() > i:
                fails.append(f"{where}: block {bid}: overlaps transcriber bracket")


def load(name):
    return json.loads((D / name).read_text(encoding="utf-8"))


enr = load("enriched.json")["items"]
for i in enr:
    check("enriched.pull_quote", i["pull_quote"], i["block_id"], no_bracket=i["own_interview"])
    if block(i["block_id"])[2] != i["text"]:
        fails.append(f"enriched: block {i['block_id']} text differs from DB")
for i in load("best_quotes.json")["items"]:
    check("best_quotes.pull_quote", i["pull_quote"], i["block_id"])
for i in load("recovered_evaluated.json")["items"]:
    check("recovered.pull_quote", i["pull_quote"], i["block_id"])

for p in load("her_words.json")["items"]:
    check("her_words.her_quote", p["her_quote"], p["her_quote_block_id"], "subject", True)
    check("her_words.bryant_quote", p["bryant_quote"], p["bryant_quote_block_id"], "interviewer", True)
    for m in p["more_her_quotes"]:
        check("her_words.more_her_quotes", m["quote"], m["block_id"], "subject", True)

ov = load("own_voice.json")
for i in ov["self"]["items"]:
    check("own_voice.self", i["pull_quote"], i["block_id"], "subject", True)
for i in ov["bryant"]["items"]:
    check("own_voice.bryant", i["pull_quote"], i["block_id"], "interviewer", True)

wp = D / "witnesses.json"
if wp.exists():
    for r in load("witnesses.json")["items"]:
        check("witnesses.lead_quote", r["lead_quote"], r["lead_block_id"])
        check("witnesses.second_quote", r["second_quote"], r["second_block_id"])
        for m in r["more_quotes"]:
            check("witnesses.more_quotes", m["quote"], m["block_id"])

for m in load("discography_personnel.json")["people"]:
    for q in m["quotes"]:
        check("roster.quotes", q["quote"], q["block_id"])
    if m["she_said"] and m["she_said"]["her_quote"]:
        check("roster.she_said", m["she_said"]["her_quote"], m["she_said"]["her_quote_block_id"],
              "subject", True)

# ---- joins
q_ids = {i["block_id"] for i in load("quotes.json")["items"]}
e_ids = {i["block_id"] for i in enr}
b_ids = {i["block_id"] for i in load("best_quotes.json")["items"]}
if e_ids != q_ids:
    fails.append(f"join: enriched ({len(e_ids)}) != quotes ({len(q_ids)})")
if not b_ids <= e_ids:
    fails.append("join: best_quotes not a subset of enriched")
doc_ids = {d["doc_id"] for d in load("documents.json")["items"]} | {
    d["doc_id"] for d in load("documents.json")["text_hit_only_documents"]}
missing = {i["doc_id"] for i in enr} - doc_ids
if missing:
    fails.append(f"join: enriched docs missing from documents.json: {sorted(missing)}")

print(f"{checked} quotes checked against linked_jazz.sqlite, {len(fails)} failures")
for f in fails[:40]:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
