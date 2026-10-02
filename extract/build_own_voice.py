#!/usr/bin/env python3
"""Merge the own-voice reading passes into liston/own_voice.json.

Three things only her own interview can give, none of which existed for
Coltrane or Davis:

  self      Liston on herself -- her life and work in her own words
  bryant    Clora Bryant on Liston -- a peer's testimony, said to her face
  timeline  the biographical facts the transcript itself states, in order

All selected by Opus subagents working to extract/OWN_VOICE_SPEC.md after
reading the whole transcript. Every quote is re-verified here: an exact
substring of ONE block, spoken by the right voice, outside any transcriber's
bracketed summary. A quote that fails is dropped and counted, never repaired.

Each item also gets the exchange it sits in (the turns around it), so a page can
show Bryant's question above Liston's answer without fetching the transcript.
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
BRACKET = re.compile(r"\[[^\]]{26,}\]")
THEMES = ["origins", "learning", "first_work", "big_bands", "the_road", "being_a_woman", "race",
          "arranging", "composing", "the_trombone", "own_bands", "randy_weston", "studio_work",
          "leaving_music", "jamaica", "teaching", "stroke", "money_and_credit", "music_today",
          "character"]
# Section headings Pass C of the category pass asked to change: singing is filed
# with her playing, and the stroke section also holds the 1996 taking-stock lines.
CATEGORY_LABELS = {"the_trombone": "Playing and Singing", "after_the_stroke": "The Stroke and After"}


def load_categories():
    """The category pass (extract/CATEGORY_SPEC.md): one scheme, two independent
    sorts, and an adjudication of the quotes the two sorts disagree on. Returns
    (scheme, {block_id: assignment}); empty when the pass has not been run."""
    o = D / "own_voice_output"
    need = [o / n for n in ("category_scheme.json", "category_a.json", "category_b.json")]
    if not all(p.exists() for p in need):
        return None, {}
    scheme, a, b = (json.loads(p.read_text(encoding="utf-8")) for p in need)
    keys = {c["key"] for c in scheme["categories"]}
    adj_p = o / "category_adjudicated.json"
    adj = {e["block_id"]: e for e in json.loads(adj_p.read_text(encoding="utf-8"))["items"]} \
        if adj_p.exists() else {}
    a = {e["block_id"]: e for e in a["items"]}
    b = {e["block_id"]: e for e in b["items"]}

    def sec(e, primary):
        s = e.get("secondary")
        return s if s in keys and s != primary else None

    out = {}
    for bid in a.keys() & b.keys():
        x, y = a[bid], b[bid]
        if bid in adj and adj[bid].get("category") in keys:
            # Pass C: a disagreement settled, or an agreed answer overruled
            e = adj[bid]
            out[bid] = {"category": e["category"], "secondary": sec(e, e["category"]),
                        "agreed": x["category"] == y["category"] == e["category"],
                        "reason": e.get("reason") or ""}
        elif x["category"] == y["category"] and x["category"] in keys:
            # a secondary stands only when both readers named the same one
            s = sec(x, x["category"])
            out[bid] = {"category": x["category"],
                        "secondary": s if s == sec(y, y["category"]) else None,
                        "agreed": True, "reason": ""}
    return scheme, out


def main():
    own = json.loads((D / "own_interview.json").read_text(encoding="utf-8"))
    order = own["items"]
    pos = {b["block_id"]: n for n, b in enumerate(order)}
    dropped = Counter()

    def verify(quote, bid, role, what):
        if not quote or bid not in pos:
            dropped[f"{what}: missing"] += 1
            return None
        b = order[pos[bid]]
        if b["speaker_role"] != role:
            dropped[f"{what}: wrong speaker"] += 1
            return None
        if quote not in b["text"]:
            dropped[f"{what}: not verbatim"] += 1
            return None
        i = b["text"].index(quote)
        for m in BRACKET.finditer(b["text"]):
            if m.start() < i + len(quote) and m.end() > i:
                dropped[f"{what}: overlaps a transcriber bracket"] += 1
                return None
        return b

    def turn(b):
        return {"block_id": b["block_id"], "page": b["page"], "speaker": b["speaker_effective"],
                "role": b["speaker_role"], "text": b["text"]}

    def exchange(bid, before=2, after=1):
        n = pos[bid]
        return {"before": [turn(b) for b in order[max(0, n - before):n] if b["speaker_role"] != "none"],
                "after": [turn(b) for b in order[n + 1:n + 1 + after] if b["speaker_role"] != "none"]}

    def has_editorial_bracket(q):
        return bool(re.search(r"\[[^\]]{1,25}\]", q))

    # ---------------- self
    raw = json.loads((D / "own_voice_output" / "self.json").read_text(encoding="utf-8"))
    top = raw.get("top") or []
    self_items = []
    for e in raw["items"]:
        b = verify(e.get("pull_quote"), e.get("block_id"), "subject", "self")
        if b is None:
            continue
        themes = [t for t in (e.get("theme") or []) if t in THEMES]
        self_items.append({
            "block_id": b["block_id"], "page": b["page"], "block": b["block"],
            "pull_quote": e["pull_quote"],
            "text": b["text"],
            "theme": themes,
            "period": e.get("period") or "",
            "summary": e.get("summary") or "",
            "prompted_by": e.get("prompted_by") or "",
            "stands_alone": bool(e.get("stands_alone")),
            "context_block_ids": [c for c in (e.get("context_block_ids") or []) if c in pos],
            "stance": e.get("stance"),
            "notable": e.get("notable") or 0,
            "is_top": b["block_id"] in top,
            "top_rank": top.index(b["block_id"]) + 1 if b["block_id"] in top else None,
            "contains_editorial_bracket": has_editorial_bracket(e["pull_quote"]),
            "whole_block": e["pull_quote"].strip() == b["text"].strip(),
            "notes": e.get("notes") or "",
            "exchange": exchange(b["block_id"]),
            "url": b["transcript_url"],
        })
    self_items.sort(key=lambda i: (-i["notable"], i["top_rank"] or 99, i["block_id"]))

    # ---------------- bryant
    rawb = json.loads((D / "own_voice_output" / "bryant.json").read_text(encoding="utf-8"))
    topb = rawb.get("top") or []
    bry = []
    for e in rawb["items"]:
        b = verify(e.get("pull_quote"), e.get("block_id"), "interviewer", "bryant")
        if b is None:
            continue
        rb = e.get("liston_response_block_id")
        resp = order[pos[rb]] if rb in pos and order[pos[rb]]["speaker_role"] == "subject" else None
        bry.append({
            "block_id": b["block_id"], "page": b["page"], "block": b["block"],
            "pull_quote": e["pull_quote"], "text": b["text"],
            "kind": e.get("kind"), "about": e.get("about") or "",
            "summary": e.get("summary") or "",
            "liston_response": e.get("liston_response"),
            "liston_response_block_id": resp["block_id"] if resp else None,
            "liston_response_text": resp["text"] if resp else None,
            "stance": e.get("stance"), "stance_strength": e.get("stance_strength") or 0,
            "notable": e.get("notable") or 0,
            "is_top": b["block_id"] in topb,
            "top_rank": topb.index(b["block_id"]) + 1 if b["block_id"] in topb else None,
            "notes": e.get("notes") or "",
            "exchange": exchange(b["block_id"], before=1, after=2),
            "url": b["transcript_url"],
        })
    bry.sort(key=lambda i: (-i["notable"], i["top_rank"] or 99, i["block_id"]))

    # ---------------- categories: the page section each pull quote sits in
    scheme, cats = load_categories()
    uncategorised = 0
    for i in self_items + bry:
        c = cats.get(i["block_id"])
        if scheme and not c:
            uncategorised += 1
        i["category"] = c["category"] if c else None
        i["category_secondary"] = c["secondary"] if c else None
        i["category_agreed"] = c["agreed"] if c else None
        i["category_note"] = c["reason"] if c else ""
    categories = []
    for n, c in enumerate((scheme or {}).get("categories") or []):
        categories.append({
            "key": c["key"], "label": CATEGORY_LABELS.get(c["key"], c["label"]), "order": n + 1, "definition": c["definition"],
            "liston": sum(1 for i in self_items if i["category"] == c["key"]),
            "bryant": sum(1 for i in bry if i["category"] == c["key"]),
            "liston_notable_2plus": sum(1 for i in self_items
                                        if i["category"] == c["key"] and i["notable"] >= 2),
        })

    # ---------------- timeline
    tl = []
    for n, e in enumerate(raw.get("timeline") or []):
        bids = [x for x in (e.get("block_ids") or []) if x in pos]
        tl.append({
            "order": n + 1, "when": e.get("when") or "", "sort_year": e.get("sort_year"),
            "event": e.get("event") or "", "stated_by": e.get("stated_by"),
            "confirmed_by_liston": bool(e.get("confirmed_by_liston")),
            "block_ids": bids,
            "url": order[pos[bids[0]]]["transcript_url"] if bids else None,
            "notes": e.get("notes") or "",
        })

    stats = {
        "self": {
            "count": len(self_items),
            "by_notable": dict(sorted(Counter(i["notable"] for i in self_items).items(), reverse=True)),
            "by_theme": dict(Counter(t for i in self_items for t in i["theme"]).most_common()),
            "stand_alone": sum(1 for i in self_items if i["stands_alone"]),
            "with_editorial_bracket": sum(1 for i in self_items if i["contains_editorial_bracket"]),
        },
        "bryant": {
            "count": len(bry),
            "by_notable": dict(sorted(Counter(i["notable"] for i in bry).items(), reverse=True)),
            "by_kind": dict(Counter(i["kind"] for i in bry).most_common()),
            "liston_response": dict(Counter(i["liston_response"] for i in bry).most_common()),
        },
        "timeline": {
            "count": len(tl),
            "stated_by": dict(Counter(i["stated_by"] for i in tl).most_common()),
            "confirmed_by_liston": sum(1 for i in tl if i["confirmed_by_liston"]),
            "undated": sum(1 for i in tl if i["sort_year"] is None),
        },
        "quotes_dropped_on_verification": dict(dropped),
    }
    if scheme:
        allq = self_items + bry
        stats["categories"] = {
            "count": len(categories),
            "by_category": {c["key"]: {"liston": c["liston"], "bryant": c["bryant"]}
                            for c in categories},
            "two_readers_agreed": sum(1 for i in allq if i["category_agreed"]),
            "adjudicated": sum(1 for i in allq if i["category_agreed"] is False),
            "with_secondary": sum(1 for i in allq if i["category_secondary"]),
            "uncategorised": uncategorised,
        }
    out = {
        "subject": SUBJ.KEY, "qid": SUBJ.QID,
        "generated_from": "linked_jazz.sqlite + Opus subagent reading pass (extract/OWN_VOICE_SPEC.md)",
        "doc": {"doc_id": SUBJ.OWN_DOC, "title": own["doc"]["title"],
                "interview_dates": "1996-12-04/1996-12-05", "place": "Los Angeles, at her home",
                "interviewer": SUBJ.INTERVIEWER, "transcript_url": own["doc"]["transcript_url"],
                "source_url": own["doc"]["source_url"]},
        "read_this_first": (
            "The interview was recorded eleven years after Liston's 1985 stroke. She had memory "
            "loss and difficulty speaking; her turns are short and the transcriber replaced "
            "stretches with bracketed summaries. No pull_quote here contains a transcriber's "
            "summary. `stands_alone: false` means the line needs the exchange around it -- it is "
            "in `exchange`. Bryant's dates and facts are Bryant's: check `liston_response`, "
            "Liston often corrects or cannot confirm them. Timeline entries with stated_by "
            "'bryant' or 'transcriber' and confirmed_by_liston false are not her testimony."),
        "themes": THEMES,
        "categories": categories,
        "stats": stats,
        "self": {"count": len(self_items), "top": [i["block_id"] for i in self_items if i["is_top"]],
                 "items": self_items},
        "bryant": {"count": len(bry), "top": [i["block_id"] for i in bry if i["is_top"]],
                   "items": bry},
        "timeline": {"count": len(tl), "items": tl},
    }
    (D / "own_voice.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "shared" / "own_voice_summary.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"own_voice.json  self {len(self_items)}  bryant {len(bry)}  timeline {len(tl)}  "
          f"dropped {dict(dropped)}")
    print("  self notable", stats["self"]["by_notable"], " bryant notable", stats["bryant"]["by_notable"])
    print("  themes", stats["self"]["by_theme"])
    if scheme:
        print("  categories (hers / Bryant's):")
        for c in categories:
            print(f"    {c['liston']:3d} / {c['bryant']:2d}  {c['label']}")
        if uncategorised:
            print(f"  !! {uncategorised} pull quotes have no category -- re-run the category pass")
    print("  her top lines:")
    for i in self_items[:12]:
        print(f"    [{i['notable']}] p{i['page']:<3} {i['pull_quote'][:110]!r}")


if __name__ == "__main__":
    main()
