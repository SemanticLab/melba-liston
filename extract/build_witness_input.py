#!/usr/bin/env python3
"""Package one bundle per WITNESS for the row-level judgement.

The evaluation pass judged blocks. A page shows people: "Slide Hampton -- joined
the band she was musical director of -- [quote]". Going from blocks to people
needs three decisions the Coltrane / Davis build made with a local Qwen model in
two separate scripts (reclassify_knows_of.py, gen_one_liners.py):

  * what is this person's relation to her, really? The upstream relation is
    `knows of` for 8 of 19 rows, and five documents that turned out to discuss
    her (the fts_supplement ones) have no upstream row at all;
  * which of their blocks should lead;
  * the short "how they knew her" phrase.

Here all three go to one Opus subagent (extract/WITNESS_SPEC.md), which sees
everything one interviewee said about her at once.

A witness = one interview document, other than her own, in which at least one
block was judged to be about her. Clora Bryant is added as a witness too: her
testimony is inside Liston's own interview (own_voice.json -> bryant).

Output: liston/witness_input.json
"""

import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY


def main():
    enr = json.loads((D / "enriched.json").read_text(encoding="utf-8"))["items"]
    rec = json.loads((D / "recovered_evaluated.json").read_text(encoding="utf-8"))["items"]
    rels = json.loads((D / "relationships.json").read_text(encoding="utf-8"))["items"]
    rel_by_doc = defaultdict(list)
    for r in rels:
        rel_by_doc[r["src"]["doc_id"]].append(r)

    con = sqlite3.connect(f"file:{SUBJ.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    itv = defaultdict(list)
    for r in con.execute("SELECT doc_id,label,qid,node_key FROM doc_interviewees ORDER BY doc_id,ord"):
        itv[r["doc_id"]].append({"label": r["label"], "qid": r["qid"] or None,
                                 "node_key": r["node_key"]})
    docs = {r["doc_id"]: dict(r) for r in con.execute(
        "SELECT doc_id,collection,title,interviewee,interviewer,year,transcript_url,source_url "
        "FROM documents")}
    wd = {r["qid"]: dict(r) for r in con.execute(
        "SELECT qid,label,description,birth,death FROM wd_people")}
    con.close()

    by_doc = defaultdict(list)
    for i in enr:
        if i["own_interview"] or not i["is_about_subject"]:
            continue
        by_doc[i["doc_id"]].append(i)
    rec_by_doc = defaultdict(list)
    for i in rec:
        if i["is_about_subject"]:
            rec_by_doc[i["doc_id"]].append(i)

    def ctx(turns, n, tail):
        turns = turns[-n:] if tail else turns[:n]
        return [{"block_id": t["block_id"], "speaker": t["speaker"], "text": t["text"]} for t in turns]

    items = []
    for did in sorted(set(by_doc) | set(rec_by_doc)):
        d = docs[did]
        people = [{**p, **{k: (wd.get(p["qid"]) or {}).get(k) for k in ("description", "birth", "death")}}
                  for p in itv.get(did, [])]
        blocks = []
        for i in sorted(by_doc.get(did, []), key=lambda x: (x["page"], x["block"])):
            blocks.append({
                "block_id": i["block_id"], "kind": "mention",
                "speaker": i["speaker"], "speaker_role": i["speaker_role"],
                "mention_kind": i["mention_kind"], "notable": i["notable"],
                "stance": i["stance"], "summary": i["summary"],
                "pull_quote": i["pull_quote"], "notes": i["notes"],
                "context_before": ctx(i["context_before"], 4, True),
                "text": i["text"],
                "context_after": ctx(i["context_after"], 4, False),
            })
        for i in sorted(rec_by_doc.get(did, []), key=lambda x: x["block_id"]):
            blocks.append({
                "block_id": i["block_id"], "kind": "recovered_" + i["source"],
                "speaker": i["speaker"], "speaker_role": None,
                "mention_kind": i["mention_kind"], "notable": i["notable"],
                "stance": i["stance"], "summary": i["summary"],
                "pull_quote": i["pull_quote"], "notes": i["notes"],
                "context_before": [{"block_id": i["anchor"]["block_id"],
                                    "speaker": i["anchor"]["speaker"], "text": i["anchor"]["text"]}],
                "text": i["text"], "context_after": [],
            })
        items.append({
            "witness_key": did,
            "doc": {k: d[k] for k in ("doc_id", "collection", "title", "interviewee", "interviewer", "year")},
            "interviewees": people,
            "upstream_relations": [{"relation": r["relation"], "direction": r["direction"],
                                    "evidence": r["evidence"], "said_by": r["person"]["name"]}
                                   for r in rel_by_doc.get(did, [])],
            "n_blocks": len(blocks),
            "blocks": blocks,
        })

    # Clora Bryant, from inside Liston's own interview
    bp = D / "own_voice_output" / "bryant.json"
    if bp.exists():
        own = {b["block_id"]: b for b in json.loads(
            (D / "own_interview.json").read_text(encoding="utf-8"))["items"]}
        order = [b["block_id"] for b in json.loads(
            (D / "own_interview.json").read_text(encoding="utf-8"))["items"]]
        pos = {b: n for n, b in enumerate(order)}
        blocks = []
        for i in json.loads(bp.read_text(encoding="utf-8"))["items"]:
            if (i.get("notable") or 0) < 2 or i["block_id"] not in own:
                continue
            n = pos[i["block_id"]]
            blocks.append({
                "block_id": i["block_id"], "kind": "bryant_testimony",
                "speaker": "Bryant", "speaker_role": "interviewer",
                "mention_kind": i["kind"], "notable": i["notable"], "stance": i.get("stance"),
                "summary": i["summary"], "pull_quote": i["pull_quote"], "notes": i.get("notes", ""),
                "context_before": [{"block_id": b, "speaker": own[b]["speaker_effective"],
                                    "text": own[b]["text"]} for b in order[max(0, n - 2):n]],
                "text": own[i["block_id"]]["text"],
                "context_after": [{"block_id": b, "speaker": own[b]["speaker_effective"],
                                   "text": own[b]["text"]} for b in order[n + 1:n + 3]],
            })
        q = SUBJ.INTERVIEWER["qid"]
        items.append({
            "witness_key": SUBJ.OWN_DOC + "#bryant",
            "doc": {"doc_id": SUBJ.OWN_DOC, "collection": "si",
                    "title": "Melba Liston — Smithsonian Jazz Oral History",
                    "interviewee": "Melba Liston", "interviewer": "Clora Bryant", "year": 1996},
            "interviewees": [{"label": "Clora Bryant", "qid": q, "node_key": f"wd:{q}",
                              **{k: (wd.get(q) or {}).get(k) for k in ("description", "birth", "death")}}],
            "is_her_interviewer": True,
            "upstream_relations": [],
            "n_blocks": len(blocks),
            "blocks": blocks,
        })

    (D / "witness_input.json").write_text(json.dumps(
        {"subject": SUBJ.KEY, "qid": SUBJ.QID, "count": len(items), "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"witness_input.json: {len(items)} witnesses, "
          f"{sum(i['n_blocks'] for i in items)} blocks, "
          f"{(D / 'witness_input.json').stat().st_size // 1024} KB")
    for i in items:
        print(f"   {i['n_blocks']:3}  {i['witness_key'][:44]:46} "
              f"{', '.join(p['label'] for p in i['interviewees'])[:40]:42} "
              f"upstream={[r['relation'] for r in i['upstream_relations']]}")


if __name__ == "__main__":
    main()
