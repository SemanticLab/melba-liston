#!/usr/bin/env python3
"""shared/class_of_1926.json -- Liston beside the other two 1926 centennials.

John Coltrane (23 Sep 1926), Miles Davis (26 May 1926) and Melba Liston (13 Jan
1926) were born within nine months of each other, and the first two already have
a centennial build (~/git/linked-jazz-coltrane-davis, read-only here). That
build had to say "there is no direct Coltrane-Davis edge" because neither man
was ever interviewed. Liston was, so for her the direct evidence can exist: what
she herself said about each of them.

For each man this gathers, from data already built:
  she_said            her_words.json entry for him, if she named him
  direct_edge         the Linked Jazz network edge between them, if any
  shared_neighbours   people with an edge to both (from the corpus DB)
  documents_naming_both   interviews whose person layer has both
  shared_releases     releases in both discographies (matched on Wikidata QID)
  shared_roster       people credited on records with both

Nothing here is judged; it is all joins.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY
OTHER_REPO = Path("/Users/m/git/linked-jazz-coltrane-davis")
OTHERS = {"coltrane": ("Q7346", "John Coltrane", "1926-09-23"),
          "davis": ("Q93341", "Miles Davis", "1926-05-26")}


def main():
    con = sqlite3.connect(f"file:{SUBJ.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    hw = {p["qid"]: p for p in json.loads((D / "her_words.json").read_text(encoding="utf-8"))["items"]
          if p.get("qid")}
    disc = json.loads((D / "discography.json").read_text(encoding="utf-8"))["releases"]
    roster = {p["qid"]: p for p in json.loads(
        (D / "discography_personnel.json").read_text(encoding="utf-8"))["people"] if p["qid"]}

    def neighbours(node):
        out = {}
        for r in con.execute("SELECT a,b,weight,n FROM edges WHERE a=? OR b=?", (node, node)):
            out[r["b"] if r["a"] == node else r["a"]] = {"weight": r["weight"], "n": r["n"]}
        return out

    mine = neighbours(SUBJ.NODE_ID)
    my_docs = {r["doc_id"] for r in con.execute("SELECT doc_id FROM persons WHERE qid=?", (SUBJ.QID,))}

    out = {}
    for key, (qid, name, born) in OTHERS.items():
        node = f"wd:{qid}"
        theirs = neighbours(node)
        both = sorted(set(mine) & set(theirs) - {node, SUBJ.NODE_ID},
                      key=lambda n: -(mine[n]["weight"] + theirs[n]["weight"]))
        labels = {r["node_id"]: dict(r) for r in con.execute(
            f"SELECT node_id,label,qid FROM nodes WHERE node_id IN ({','.join('?' * len(both))})",
            both)} if both else {}
        edge = con.execute(
            "SELECT edge_id,a,b,weight,n,pair_fnv FROM edges WHERE (a=? AND b=?) OR (a=? AND b=?)",
            (node, SUBJ.NODE_ID, SUBJ.NODE_ID, node)).fetchone()
        rels = []
        if edge:
            rels = [dict(r) for r in con.execute(
                "SELECT relation,count,direction FROM edge_relations WHERE edge_id=?",
                (edge["edge_id"],))]
        their_docs = {r["doc_id"] for r in con.execute(
            "SELECT doc_id FROM persons WHERE qid=?", (qid,))}
        docs_both = sorted(my_docs & their_docs)
        doc_rows = [dict(r) for r in con.execute(
            f"SELECT doc_id,title,collection,interviewee,year,transcript_url FROM documents "
            f"WHERE doc_id IN ({','.join('?' * len(docs_both))})", docs_both)] if docs_both else []

        shared_rel, shared_people = [], []
        od = OTHER_REPO / key / "discography.json"
        if od.exists():
            theirs_q = {r["qid"]: r for r in json.loads(od.read_text(encoding="utf-8"))["releases"]
                        if r.get("qid")}
            for r in disc:
                if r["qid"] and r["qid"] in theirs_q:
                    shared_rel.append({"title": r["title"], "qid": r["qid"], "year": r["year"],
                                       "her_role": r["subject_role"],
                                       "her_credit": r["subject_credit"]["roles"],
                                       "his_role": theirs_q[r["qid"]].get("subject_role"),
                                       "wikipedia_url": r["wikipedia_url"]})
        op = OTHER_REPO / key / "discography_personnel.json"
        if op.exists():
            for p in json.loads(op.read_text(encoding="utf-8"))["people"]:
                m = roster.get(p.get("qid"))
                if m and p["qid"] not in (qid, SUBJ.QID):
                    shared_people.append({"name": m["name"], "qid": m["qid"],
                                          "albums_with_her": m["album_count"],
                                          "albums_with_him": p["album_count"],
                                          "said_about_her": m["said_about_subject"],
                                          "said_about_him": p.get("said_about_subject", False),
                                          "she_spoke_of_them": m["she_spoke_of_them"]})
            shared_people.sort(key=lambda x: -(x["albums_with_her"] + x["albums_with_him"]))

        h = hw.get(qid)
        out[key] = {
            "name": name, "qid": qid, "born": born,
            "she_said": ({k: h[k] for k in (
                "relation", "direction", "basis", "who_speaks_of_them", "summary", "one_liner",
                "her_quote", "her_quote_url", "bryant_quote", "bryant_quote_url", "era", "notable",
                "notes")} if h else None),
            "on_her_records": qid in roster,
            "albums_together": roster[qid]["albums"] if qid in roster else [],
            "direct_edge": ({"weight": edge["weight"], "n": edge["n"], "relations": rels,
                             "evidence_url": "https://thisismattmiller.github.io/linked-jazz-2026-network/"
                                             f"ev/{edge['pair_fnv'][:2]}/{edge['pair_fnv']}.json"}
                            if edge else None),
            "shared_neighbours": {
                "count": len(both),
                "jaccard": round(len(both) / max(1, len(set(mine) | set(theirs))), 4),
                "her_neighbours": len(mine), "his_neighbours": len(theirs),
                "top": [{"node_id": n, "label": labels.get(n, {}).get("label"),
                         "qid": labels.get(n, {}).get("qid"),
                         "her_weight": mine[n]["weight"], "his_weight": theirs[n]["weight"]}
                        for n in both[:40]]},
            "documents_naming_both": {"count": len(doc_rows), "items": doc_rows},
            "shared_releases": {"count": len(shared_rel), "items": shared_rel,
                                "available": od.exists()},
            "shared_roster": {"count": len(shared_people), "items": shared_people[:80],
                              "available": op.exists()},
        }
        e = out[key]
        print(f"{name}: she_said={'yes' if h else 'no'} edge={'yes' if edge else 'no'} "
              f"shared neighbours={len(both)} (J={e['shared_neighbours']['jaccard']}) "
              f"docs naming both={len(doc_rows)} shared releases={len(shared_rel)} "
              f"shared roster={len(shared_people)}")
        if h:
            print(f"   relation={h['relation']} basis={h['basis']} quote={h['her_quote']!r} "
                  f"bryant={(h['bryant_quote'] or '')[:90]!r}")

    (ROOT / "shared" / "class_of_1926.json").write_text(json.dumps({
        "subject": SUBJ.KEY, "qid": SUBJ.QID,
        "generated_from": "linked_jazz.sqlite + this repo + ~/git/linked-jazz-coltrane-davis (read-only)",
        "note": "Three jazz musicians born in 1926. All joins; nothing judged here except the "
                "she_said blocks, which come from her_words.json.",
        "liston": {"name": SUBJ.NAME, "qid": SUBJ.QID, "born": "1926-01-13"},
        "others": out,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
