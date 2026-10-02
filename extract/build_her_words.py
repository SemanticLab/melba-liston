#!/usr/bin/env python3
"""Merge the her-words judgement chunks into liston/her_words.json.

her_relationships.json is what the upstream model thought Liston said about the
people in her interview. This is what four Opus subagents, each having read the
whole transcript, judged she actually said (extract/HER_WORDS_SPEC.md) -- plus
the people the automatic name detection missed (Part C of
extract/OWN_VOICE_SPEC.md).

Nothing a judge wrote is trusted without re-checking it against the transcript:
every quote must be an exact substring of ONE block spoken by the right voice,
and a quote that fails is dropped (and counted), never repaired.

Judges also flagged entries that are the same person under two labels. Those
merges are judgement calls made by the readers; they are recorded in MERGES
below with the reader's reason, applied here, and the absorbed records are kept
under `merged` so every one can be undone.

Outputs
  liston/her_words.json        one record per person, judged, ranked
  shared/her_words_summary.json
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY
NETWORK = "https://thisismattmiller.github.io/linked-jazz-2026-network/#"

RELATIONS = {"in music group with", "collaborated with", "played with", "toured with",
             "played under", "mentor of", "influenced by", "friend of", "acquaintance of",
             "has met", "knows of", "none"}
DIRECTIONS = {"other_leads", "liston_leads", "mutual", "na"}

# absorbed person_id -> (kept person_id, who said so and why)
MERGES = {
    104476: (104388, "'Mrs. H[?(inaudible)]' is Liston's partly inaudible attempt at Alice "
                     "Young's married name (block 295573) -- reader of chunk 1"),
    104473: (104435, "'Boo - Boo Pleasant' and 'Bu Pleasant - a saxophonist' are one person; "
                     "the transcript also has 'Boo Pleasant' (295782) and 'Bu' (295976) -- "
                     "readers of chunks 2 and 4"),
    104411: (104391, "'Elvira' is Vi Redd (born Elvira Redd): Liston names 'Elvira' in the band "
                     "photograph (296316) and Bryant glosses it 'Elvira - Vi Redd's brother' "
                     "(296319, garbled) -- readers of chunks 1 and 4; medium confidence"),
    104490: (104489, "'Moore' and 'Morris' are the transcriber's two guesses at one surname, "
                     "'Minnie [?Moore ?Morris]', for a girl in the c.1938 band photograph -- "
                     "reader of chunk 4"),
}
# flagged by readers but NOT merged, because the reader was not sure enough
UNMERGED_LEADS = [
    {"person_ids": [104489, 104376],
     "note": "'Minnie [?Moore ?Morris]' in the c.1938 band photograph is 'almost certainly' "
             "Minnie Hightower (reader of chunk 4) -- left separate; low confidence"},
    {"person_ids": [104376],
     "note": "'Minnie Hightower' folds two people: Minnie, Liston's schoolmate and bandmate, and "
             "her mother Mrs./Miss Hightower, the teacher who led the Melodic Dots. The record "
             "describes the mother; Minnie's own lines are in its notes. Needs splitting by hand "
             "(reader of chunk 1)."},
    {"person_ids": [104415],
     "note": "'Clifford, Jr.' folds Minnie Hightower's son (a preacher, per Bryant) with his "
             "father Clifford Burden, the man in the 1930s photograph (reader of chunk 4)."},
    {"person_ids": [104384],
     "note": "One mention folded into Ray Charles (296209, 'it didn't feature Ray') is almost "
             "certainly trumpeter Ray Copeland (reader of chunk 3)."},
    {"person_ids": [104398],
     "note": "The bare 'Jimmie' in 296492 ('Stacey Rowles. Jimmie's daughter.') is Jimmie "
             "Rowles, not Jimmie Lunceford (reader of chunk 1)."},
]

# identity_ok=false means one of two things: the Wikidata match is wrong, or the
# match is right but a stray mention of somebody else was folded in. For these
# the reader said explicitly that the QID is right for the person the record
# describes, so the QID is kept and the stray mention is described in
# identity_note. Anything else with identity_ok=false loses its QID.
QID_RIGHT_BUT_FOLD_CONTAMINATED = {104384, 104398}   # Ray Charles, Jimmie Lunceford

BRACKET = re.compile(r"\[[^\]]{26,}\]")


def main():
    own = json.loads((D / "own_interview.json").read_text(encoding="utf-8"))
    blocks = {b["block_id"]: b for b in own["items"]}
    hr = json.loads((D / "her_relationships.json").read_text(encoding="utf-8"))
    up = {x["person"]["person_id"]: x for x in hr["items"] + hr["skipped"]["items"]}
    weights = hr["relation_weights"]

    dropped = Counter()

    def check(quote, bid, role, what):
        """-> (quote, block) if it verifies, else (None, None)."""
        if not quote:
            return None, None
        b = blocks.get(bid)
        if b is None:
            dropped[f"{what}: block not in interview"] += 1
            return None, None
        if b["speaker_role"] != role:
            dropped[f"{what}: wrong speaker"] += 1
            return None, None
        if quote not in b["text"]:
            dropped[f"{what}: not verbatim"] += 1
            return None, None
        i = b["text"].index(quote)
        for m in BRACKET.finditer(b["text"]):
            if m.start() < i + len(quote) and m.end() > i:
                dropped[f"{what}: overlaps a transcriber bracket"] += 1
                return None, None
        return quote, b

    def shape(e, u, source):
        hq, hb = check(e.get("her_quote"), e.get("her_quote_block_id"), "subject", "her_quote")
        bq, bb = check(e.get("bryant_quote"), e.get("bryant_quote_block_id"), "interviewer",
                       "bryant_quote")
        more = []
        for m in e.get("more_her_quotes") or []:
            q, b = check(m.get("quote"), m.get("block_id"), "subject", "more_her_quotes")
            if q and q != hq:
                more.append({"block_id": b["block_id"], "quote": q, "page": b["page"],
                             "url": b["transcript_url"]})
        rel = e.get("relation") if e.get("relation") in RELATIONS else "none"
        if rel != e.get("relation"):
            dropped["relation outside vocabulary -> none"] += 1
        dirn = e.get("direction") if e.get("direction") in DIRECTIONS else "na"
        p = (u or {}).get("person") or {}
        ok = bool(e.get("identity_ok", True))
        qid = p.get("qid") if (ok or e.get("person_id") in QID_RIGHT_BUT_FOLD_CONTAMINATED) else None
        return {
            "person_id": e.get("person_id"),
            "source": source,
            "name": e.get("name") or p.get("name"),
            "as_named_in_interview": p.get("as_named_in_interview") or (e.get("as_in_transcript") or [None])[0],
            "also_named": list(e.get("as_in_transcript") or p.get("surface_forms") or []),
            "is_person": bool(e.get("is_person", True)),
            "not_person_kind": e.get("not_person_kind"),
            # ---- identity
            "qid": qid,
            "identity_ok": ok,
            "fold_contaminated": (not ok) and qid is not None,
            "identity_note": e.get("identity_note") or "",
            "upstream_qid": p.get("qid"),
            "description": p.get("description") if qid else (e.get("who_is_this") or None),
            "born": p.get("born") if qid else None,
            "died": p.get("died") if qid else None,
            "wikipedia": p.get("wikipedia") if qid else None,
            "node_keys": p.get("node_keys") or [],
            "network_url": p.get("network_url"),
            # ---- the judgement
            "who_speaks_of_them": e.get("who_speaks_of_them"),
            "basis": e.get("basis"),
            "relation": rel,
            "relation_weight": weights.get(rel, 0.0),
            "direction": dirn,
            "tie": e.get("tie") or [],
            "firsthand": bool(e.get("firsthand")),
            "stance": e.get("stance"),
            "stance_strength": e.get("stance_strength") or 0,
            "era": e.get("era") or "",
            "summary": e.get("summary") or "",
            "one_liner": e.get("one_liner") or "",
            # ---- her words (verified verbatim, right speaker, no transcriber brackets)
            "her_quote": hq,
            "her_quote_block_id": hb["block_id"] if hb else None,
            "her_quote_page": hb["page"] if hb else None,
            "her_quote_url": hb["transcript_url"] if hb else None,
            "bryant_quote": bq,
            "bryant_quote_block_id": bb["block_id"] if bb else None,
            "bryant_quote_url": bb["transcript_url"] if bb else None,
            "more_her_quotes": more,
            "n_her_quotes": (1 if hq else 0) + len(more),
            "topics": e.get("topics") or [],
            "notable": e.get("notable") or 0,
            "is_chunk_top": False,
            "confidence": e.get("confidence"),
            "notes": e.get("notes") or "",
            # ---- provenance
            "n_mentions": p.get("n_mentions") or len(e.get("block_ids") or []),
            "mention_block_ids": p.get("mention_block_ids") or e.get("block_ids") or [],
            "is_interviewer": p.get("qid") == SUBJ.INTERVIEWER["qid"],
            "upstream": {"relation": (u or {}).get("relation"),
                         "direction": (u or {}).get("direction"),
                         "evidence": (u or {}).get("evidence"),
                         "relation_ok": e.get("upstream_relation_ok")} if u else None,
        }

    items, missing, tops = {}, [], set()
    for f in sorted((D / "her_words_input").glob("chunk_*.json")):
        o = D / "her_words_output" / f.name
        if not o.exists():
            missing.append(f.name)
            continue
        want = [i["person_id"] for i in json.loads(f.read_text(encoding="utf-8"))["items"]]
        d = json.loads(o.read_text(encoding="utf-8"))
        got = [i["person_id"] for i in d["items"]]
        if got != want:
            sys.exit(f"FATAL: {o.name} person_id order differs from its input")
        tops.update(d.get("chunk_top") or [])
        for e in d["items"]:
            items[e["person_id"]] = shape(e, up.get(e["person_id"]), "person_layer")
    for pid in tops:
        if pid in items:
            items[pid]["is_chunk_top"] = True

    # ---- merges recommended by the readers
    merged = []
    for src, (dst, why) in MERGES.items():
        if src not in items or dst not in items:
            continue
        a, b = items.pop(src), items[dst]
        b["also_named"] = sorted(set(b["also_named"]) | set(a["also_named"])
                                 | {a["as_named_in_interview"]} - {None})
        b["mention_block_ids"] = sorted(set(b["mention_block_ids"]) | set(a["mention_block_ids"]))
        b["n_mentions"] += a["n_mentions"]
        b["node_keys"] = sorted(set(b["node_keys"]) | set(a["node_keys"]))
        have = {b["her_quote"]} | {m["quote"] for m in b["more_her_quotes"]}
        extra = ([{"block_id": a["her_quote_block_id"], "quote": a["her_quote"],
                   "page": a["her_quote_page"], "url": a["her_quote_url"]}]
                 if a["her_quote"] else []) + a["more_her_quotes"]
        for m in extra:
            if m["quote"] not in have:
                b["more_her_quotes"].append(m)
                have.add(m["quote"])
        if not b["her_quote"] and b["more_her_quotes"]:
            m = b["more_her_quotes"].pop(0)
            b.update(her_quote=m["quote"], her_quote_block_id=m["block_id"],
                     her_quote_page=m["page"], her_quote_url=m["url"])
        b["n_her_quotes"] = (1 if b["her_quote"] else 0) + len(b["more_her_quotes"])
        b["notable"] = max(b["notable"], a["notable"])
        b["notes"] = (b["notes"] + f" | merged: {a['as_named_in_interview']} "
                                   f"(person_id {src})").strip(" |")
        merged.append({"merged_into": dst, "reason": why, "record": a})

    # ---- people the name detection missed, found by a reader
    mp = D / "own_voice_output" / "missed_people.json"
    added = []
    if mp.exists():
        known = set()
        for it in items.values():
            for n in [it["name"], it["as_named_in_interview"], *it["also_named"]]:
                if n:
                    known.add(re.sub(r"[^a-z0-9]+", " ", n.lower()).strip())
        for e in json.loads(mp.read_text(encoding="utf-8"))["items"]:
            key = re.sub(r"[^a-z0-9]+", " ", (e.get("name") or "").lower()).strip()
            rec = shape({**e, "is_person": True, "identity_ok": True}, None, "reader_added")
            rec["possible_duplicate_of_detected_person"] = key in known
            added.append(rec)

    # A reader-added "Alma Hightower" is the teacher the person layer folded into
    # her daughter's entry (104376). Both records describe the mother, so they
    # are one record; the daughter, Minnie, still needs splitting out by hand.
    for rec in list(added):
        if rec["name"] == "Alma Hightower" and 104376 in items:
            b = items[104376]
            have = {b["her_quote"]} | {m["quote"] for m in b["more_her_quotes"]}
            if rec["her_quote"] and rec["her_quote"] not in have:
                b["more_her_quotes"].append({
                    "block_id": rec["her_quote_block_id"], "quote": rec["her_quote"],
                    "page": rec["her_quote_page"], "url": rec["her_quote_url"]})
            b["n_her_quotes"] = (1 if b["her_quote"] else 0) + len(b["more_her_quotes"])
            b["also_named"] = sorted(set(b["also_named"]) | set(rec["also_named"])
                                     | {b["name"]})
            b["name"] = "Alma Hightower"
            b["description"] = rec["description"] or b["description"]
            b["mention_block_ids"] = sorted(set(b["mention_block_ids"]) | set(rec["mention_block_ids"]))
            b["notes"] = (b["notes"] + " | The first name 'Alma' is not in the transcript; it was "
                          "supplied by a reader to identify the teacher. The upstream label for "
                          "this record was her daughter's name, Minnie Hightower.").strip(" |")
            added.remove(rec)
            merged.append({"merged_into": 104376,
                           "reason": "reader-added 'Alma Hightower' and the detected 'Minnie "
                                     "Hightower' record both describe the mother, the teacher",
                           "record": rec})

    # Reader-added people have no QID. Take one only on an exact, unique label
    # match in the corpus's own Wikidata authority table -- never a search.
    import sqlite3
    con = sqlite3.connect(f"file:{SUBJ.DB}?mode=ro", uri=True)
    for rec in added:
        rows = con.execute(
            "SELECT qid, description, birth, death, wp_title FROM wd_people WHERE label = ?",
            (rec["name"],)).fetchall()
        if len(rows) == 1 and (rows[0][1] or rows[0][2]):   # never onto a stub item
            q, desc, b_, d_, wp = rows[0]
            rec.update(qid=q, qid_source="exact unique label match in wd_people",
                       born=b_, died=d_, node_keys=[f"wd:{q}"], network_url=NETWORK + f"wd:{q}",
                       wikipedia=("https://en.wikipedia.org/wiki/" + wp.replace(" ", "_")) if wp else None)
            rec["description_from_transcript"] = rec["description"]
            rec["description"] = desc or rec["description"]
    con.close()

    people = list(items.values()) + added
    people.sort(key=lambda x: (not x["is_person"], -x["notable"], -x["relation_weight"],
                               -x["n_her_quotes"], x["name"] or ""))

    real = [p for p in people if p["is_person"]]
    rel_ok = [p["upstream"]["relation_ok"] for p in items.values()
              if p["upstream"] and p["upstream"]["relation_ok"] is not None]
    stats = {
        "entries": len(people),
        "real_people": len(real),
        "not_people": len(people) - len(real),
        "not_people_kinds": dict(Counter(p["not_person_kind"] for p in people if not p["is_person"])),
        "reader_added_people": len(added),
        "merged_duplicates": len(merged),
        "chunks_missing": missing,
        "with_a_relation": sum(1 for p in real if p["relation"] != "none"),
        "by_relation": dict(Counter(p["relation"] for p in real).most_common()),
        "by_basis": dict(Counter(p["basis"] for p in real).most_common()),
        "by_who_speaks": dict(Counter(p["who_speaks_of_them"] for p in real).most_common()),
        "by_notable": dict(sorted(Counter(p["notable"] for p in real).items(), reverse=True)),
        "by_tie": dict(Counter(t for p in real for t in p["tie"]).most_common()),
        "with_her_own_quote": sum(1 for p in real if p["her_quote"]),
        "her_quotes_total": sum(p["n_her_quotes"] for p in real),
        "reconciled_to_wikidata": sum(1 for p in real if p["qid"]),
        "identity_rejected": sum(1 for p in real if not p["identity_ok"]),
        "upstream_relation_wrong": rel_ok.count(False),
        "upstream_relation_judged": len(rel_ok),
        "upstream_relation_wrong_pct": round(100 * rel_ok.count(False) / len(rel_ok), 1) if rel_ok else 0,
        "quotes_dropped_on_verification": dict(dropped),
    }

    out = {
        "subject": SUBJ.KEY, "qid": SUBJ.QID,
        "generated_from": "linked_jazz.sqlite + Opus subagent judgement pass "
                          "(extract/HER_WORDS_SPEC.md, extract/OWN_VOICE_SPEC.md part C)",
        "direction_of_this_file": "FROM Melba Liston TO the person named",
        "count": len(people),
        "doc": {"doc_id": SUBJ.OWN_DOC, "title": own["doc"]["title"], "year": 1996,
                "interviewer": SUBJ.INTERVIEWER["name"],
                "transcript_url": own["doc"]["transcript_url"],
                "source_url": own["doc"]["source_url"]},
        "method": (
            "One record per person named in her 1996 interview. Each of four readers read the "
            "whole transcript and then judged ~30 people: is this a person at all, is the "
            "Wikidata match right, who actually speaks of them, what the relation is and what it "
            "rests on (basis), and her best verbatim line about them. Every quote here was "
            "re-verified in this script as an exact substring of one block spoken by the right "
            "voice and outside any transcriber's bracketed summary; failures are dropped and "
            "counted in stats.quotes_dropped_on_verification. source='reader_added' marks people "
            "the name detection missed. Sorted by notable, then relation weight."),
        "read_this_first": (
            "basis is the field to filter on. her_statement = she said it. her_assent = Clora "
            "Bryant said it and Liston agreed (the words are in bryant_quote). bryant_only and "
            "transcriber_summary = Liston did not say it. Liston had a stroke in 1985; many of "
            "her answers are 'Yeah.'"),
        "relation_weights": weights,
        "stats": stats,
        "merged": merged,
        "unmerged_leads": UNMERGED_LEADS,
        "items": people,
    }
    (D / "her_words.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "shared").mkdir(exist_ok=True)
    (ROOT / "shared" / "her_words_summary.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"her_words.json: {len(people)} entries -- {len(real)} people "
          f"({len(added)} reader-added), {len(people) - len(real)} not people, "
          f"{len(merged)} merged, chunks missing: {missing}")
    print(f"  with a relation: {stats['with_a_relation']}   with her own quote: "
          f"{stats['with_her_own_quote']}   her quotes total: {stats['her_quotes_total']}")
    print(f"  by basis    {stats['by_basis']}")
    print(f"  by relation {stats['by_relation']}")
    print(f"  by notable  {stats['by_notable']}")
    print(f"  upstream relation wrong: {stats['upstream_relation_wrong']}/"
          f"{stats['upstream_relation_judged']} ({stats['upstream_relation_wrong_pct']}%)")
    print(f"  quotes dropped on verification: {dict(dropped)}")
    print("  top:")
    for p in real[:12]:
        print(f"    [{p['notable']}] {p['name'][:26]:28} {p['relation']:20} {p['basis']:18} "
              f"{(p['her_quote'] or '')[:70]!r}")


if __name__ == "__main__":
    main()
