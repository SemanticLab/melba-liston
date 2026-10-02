#!/usr/bin/env python3
"""Build the page bundle: docs/data.json and the images the page shows.

Reads the judged layers under liston/ and shared/, plus two hand-authored files
in this directory (lanes.json, editorial.json), and writes everything the page
in docs/ needs. The page itself (docs/index.html, docs/app.js, docs/style.css)
is static and is not generated; nor are its two own images, docs/img/liston.png
(the hero cut-out) and docs/img/linked-jazz.png, which came with the design.

What the page shows, and from where:
  hero / blurb   profile.json, documents.json, people.json, discography.json
  timeline       own_voice.json -> timeline (the dots); site/lanes.json (the bars)
  voices         witnesses.json, filtered: only people who spoke themselves and
                 have a verbatim lead quote; site/editorial.json for the rest
  her words      own_voice.json -> self, with the category pass's sections
  discography    discography.json, shared/cover_art.json
  passages       docs/transcripts.json: the transcript text behind every quote,
                 opened in place by the page. Her own interview goes in whole;
                 each witness's interview as a window around the quoted turn,
                 read from linked_jazz.sqlite. Each carries the archive's own
                 URL -- the page links to the original, not to a reader.
"""

import json
import os
import re
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "extract"))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY
OUT = ROOT / "docs"

TIER_LABELS = [("band", "Bandmates"), ("learned", "Learned from her"),
               ("social", "Friends & acquaintances"), ("knew_of", "Knew of her")]
ROLE_LABELS = {"leader": "leader", "arranger": "arranger", "composer": "composer",
               "sidewoman": "sidewoman", "listed_unverified": "listed",
               "appears_on_screen": "on screen"}
ROLE_PILLS = [("leader", "Leader"), ("arranger", "Arranger"), ("composer", "Composer"),
              ("sidewoman", "Sidewoman")]
# cover-less releases get a colour block, as in the mockup
PALETTE = ["#D63A1F", "#3D5A3A", "#5B4A7A", "#2E5C6E", "#7A3A3A", "#6B5A2A", "#3A4A6B",
           "#5A3A6B", "#2A5A4A", "#4A3A2A", "#1C3A4A", "#6B3A5A"]
DB = "/Users/m/git/ch-jazz-mashup/linked_jazz.sqlite"
# archive name as a heading, and as the object of "Original transcript at ..."
ARCHIVES = {"si": ("Smithsonian Jazz Oral History Program", "the Smithsonian"),
            "rutgers": ("Rutgers Institute of Jazz Studies", "Rutgers"),
            "hamilton": ("Hamilton College, Fillius Jazz Archive", "Hamilton College")}
SPOKEN = ("dialogue", "prose", "note", "stage_direction")
# a witness's passage: at least this much either side of the quoted turn
WIN_MIN_BLOCKS, WIN_MIN_CHARS, WIN_MAX_BLOCKS, WIN_MAX_CHARS = 10, 3000, 16, 8000
# page furniture the Hamilton PDFs leave at the end of a turn
FOOTER = re.compile(
    r"(?:©\s*Fillius\s+Jazz\s+Archive[^A-Za-z]*(?:-\s*\d+\s*-)?|"
    r"Fillius\s+Jazz\s+Archive,\s*Hamilton\s+College[^.]*\.?|"
    r"-\s*\d+\s*-)\s*$", re.I)
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                "seventeen", "eighteen", "nineteen", "twenty", "twenty-one", "twenty-two",
                "twenty-three", "twenty-four", "twenty-five"]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_size != src.stat().st_size:
        shutil.copyfile(src, dst)


# ------------------------------------------------------------------ passages
def clean(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    prev = None
    while prev != text:
        prev = text
        text = FOOTER.sub("", text).strip()
    return text


def turn(block_id, page, kind, speaker, text):
    return {"i": block_id, "p": page, "s": (speaker or "").strip().rstrip(":"),
            "t": clean(text), **({"n": 1} if kind in ("note", "stage_direction") else {})}


def doc_entry(collection, title, url, blocks, complete):
    archive, at = ARCHIVES[collection]
    return {"title": title, "archive": archive, "at": at, "url": url,
            "pdf": url.lower().split("?")[0].endswith(".pdf"),
            "complete": complete, "blocks": [b for b in blocks if b["t"]]}


def own_transcript(own):
    d = own["doc"]
    blocks = [turn(b["block_id"], b["page"], b["type"], b["speaker_effective"], b["text"])
              for b in own["items"] if b["type"] in SPOKEN]
    return doc_entry(d["collection"], d["title"], d["source_url"], blocks, True)


def witness_transcript(db, row):
    """The turns around a witness's lead quote, from the corpus."""
    doc_id = row["doc"]["doc_id"]
    coll, title, url = db.execute(
        "select collection, title, source_url from documents where doc_id=?", (doc_id,)).fetchone()
    rows = db.execute("select block_id, page, type, speaker, text from blocks where doc_id=? "
                      "order by page, block", (doc_id,)).fetchall()
    rows = [r for r in rows if r[2] in SPOKEN]
    at = [r[0] for r in rows].index(row["lead_block_id"])

    def walk(seq):
        out, chars = [], 0
        for r in seq:
            if len(out) >= WIN_MAX_BLOCKS or chars >= WIN_MAX_CHARS:
                break
            if len(out) >= WIN_MIN_BLOCKS and chars >= WIN_MIN_CHARS:
                break
            out.append(r)
            chars += len(r[4] or "")
        return out

    window = walk(rows[:at][::-1])[::-1] + [rows[at]] + walk(rows[at + 1:])
    if coll == "si":       # several Smithsonian titles are stored surname-first
        title = f"{row['name']} — Smithsonian Jazz Oral History"
    title = re.sub(r"^\d+_", "", title)
    return doc_entry(coll, title, url, [turn(*r) for r in window], False)


# ------------------------------------------------------------------ timeline
def stated(t):
    by, ok = t["stated_by"], t["confirmed_by_liston"]
    if by == "liston":
        return "Stated by Liston"
    if by == "bryant":
        return "Stated by Clora Bryant · " + ("Liston confirms" if ok else "not confirmed by Liston")
    return "Transcriber’s summary or transcript header" + (" · Liston confirms" if ok else "")


def build_timeline(ov):
    items = ov["timeline"]["items"]
    # the list is in the order the life ran; an undated entry is placed between
    # its dated neighbours so it has somewhere to sit on the axis
    years = [t["sort_year"] for t in items]
    pos = list(years)
    n = len(items)
    i = 0
    while i < n:
        if pos[i] is None:
            j = i
            while j < n and years[j] is None:
                j += 1
            a = years[i - 1] if i else 1926
            b = years[j] if j < n else a
            for k in range(i, j):
                pos[k] = a + (b - a) * (k - i + 1) / (j - i + 1)
            i = j
        else:
            i += 1
    out = []
    for t, p in zip(items, pos):
        dec = re.search(r"\b(1[89]\d0|20\d0)s\b", t["when"] or "")
        out.append({
            "when": t["when"] or "undated",
            "year": t["sort_year"],
            "big": str(t["sort_year"]) if t["sort_year"] else (dec.group(0) if dec else ""),
            "pos": round(p, 2),
            "approx": t["sort_year"] is None,
            "event": t["event"],
            "stated": stated(t),
            "blocks": t["block_ids"],
        })
    return out


# ------------------------------------------------------------------ voices
def build_voices(wit, editorial, transcripts):
    ed = editorial["witnesses"]
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    by_person = {}
    for r in wit["items"]:
        if not (r["spoke_themselves"] and r["lead_quote"] and r["tier"] in dict(TIER_LABELS)):
            continue
        key = r["qid"] or r["name"]
        if ed.get(key, {}).get("hide"):
            continue
        by_person.setdefault(key, []).append(r)
    cards, credits = [], []
    for key, rows in by_person.items():
        rows.sort(key=lambda r: (-r["notable"], -r["relation_weight"]))
        r, e = rows[0], ed.get(key, {})
        img = None
        if r["qid"] and (ROOT / "img" / "p" / f"{r['qid']}.jpg").exists():
            img = f"img/p/{r['qid']}.jpg"
            copy(ROOT / img, OUT / img)
            im = r.get("image") or {}
            credits.append({"name": r["name"], "attribution": im.get("attribution") or "",
                            "page": im.get("commons_page")})
        if r["is_her_interviewer"]:
            doc = "own"
        else:
            doc = r["doc"]["doc_id"]
            transcripts[doc] = witness_transcript(db, r)
        shown = {b["i"] for b in transcripts[doc]["blocks"]}
        cards.append({
            "name": r["name"], "qid": r["qid"],
            "tiers": sorted({x["tier"] for x in rows}),
            "line": r["one_liner"],
            "quote": r["lead_quote"],
            "second": r["second_quote"] if e.get("show_second") else None,
            "note": e.get("note"),
            "doc": doc,
            "blocks": sorted({b for b in (r["lead_block_id"],
                                          r["second_block_id"] if e.get("show_second") else None)
                              if b in shown}),
            "source": transcripts[doc]["title"],
            "img": img,
            "notable": r["notable"], "weight": max(x["relation_weight"] for x in rows),
        })
    cards.sort(key=lambda c: (-c["notable"], -c["weight"], c["name"]))
    counts = Counter(t for c in cards for t in c["tiers"])
    tiers = [{"key": k, "label": lab, "count": counts[k]} for k, lab in TIER_LABELS if counts[k]]
    return cards, tiers, credits


# ------------------------------------------------------------------ discography
def build_releases(disc, covers):
    by_qid = {v["qid"]: mbid for mbid, v in covers["items"].items() if v.get("qid")}
    out = []
    for n, r in enumerate(sorted(disc["releases"], key=lambda r: (str(r["year"]), r["title"]))):
        leader = r.get("leader")
        if not leader:
            m = re.search(r"\bby (.+)$", r.get("description") or "")
            leader = m.group(1) if m else ""
        cover = None
        mbid = by_qid.get(r.get("qid"))
        if mbid and (ROOT / "img" / "a" / f"{mbid}.jpg").exists():
            cover = f"img/a/{mbid}.jpg"
            copy(ROOT / cover, OUT / cover)
        mb = r.get("musicbrainz")
        out.append({
            "title": re.sub(r"\s*\((?:[^()]* )?album\)$", "", r["title"]),
            "leader": leader, "year": r["year"],
            "role": r["subject_role"], "role_label": ROLE_LABELS.get(r["subject_role"], r["subject_role"]),
            "url": r.get("wikipedia_url") or (f"https://musicbrainz.org/release-group/{mb}" if mb else None),
            "cover": cover, "bg": PALETTE[n % len(PALETTE)],
        })
    roles = Counter(r["role"] for r in out)
    pills = [{"key": k, "label": lab, "count": roles[k]} for k, lab in ROLE_PILLS if roles[k]]
    return out, pills


def main():
    prof = load(D / "profile.json")["profile"]
    docs = load(D / "documents.json")
    people = load(D / "people.json")
    ov = load(D / "own_voice.json")
    wit = load(D / "witnesses.json")
    disc = load(D / "discography.json")
    covers = load(ROOT / "shared" / "cover_art.json")
    lanes = load(HERE / "lanes.json")
    editorial = load(HERE / "editorial.json")

    transcripts = {"own": own_transcript(load(D / "own_interview.json"))}
    voices, tiers, credits = build_voices(wit, editorial, transcripts)
    # the hero cut-out is made from her Commons portrait, so it carries that credit
    hero_img = load(ROOT / "shared" / "images.json")["people"][SUBJ.QID]["image"]
    credits.append({"name": "Melba Liston (cut-out at the top of the page, from)",
                    "attribution": hero_img["attribution"], "page": hero_img["commons_page"]})
    releases, role_pills = build_releases(disc, covers)
    cats = {c["key"]: c for c in ov["categories"]}
    own = [{"q": i["pull_quote"], "cat": i["category"], "alone": i["stands_alone"],
            "sum": i["summary"], "b": i["block_id"], "n": i["notable"]}
           for i in ov["self"]["items"]]
    if any(o["cat"] not in cats for o in own):
        sys.exit("own_voice.json has pull quotes with no category -- run the category pass")

    wd = prof["wd_people"]
    data = {
        "generated_by": "site/build_site_data.py",
        "hero": {
            "name": prof["display_name"],
            "tagline": editorial["tagline"],
            "stats": [
                {"n": disc["count"], "label": "releases"},
                {"n": len(docs["items"]) + len(docs["text_hit_only_documents"]),
                 "label": "interviews that name her"},
                {"n": people["count"], "label": "people in her circle"},
            ],
        },
        "blurb": {
            "text": wd["wp_abstract"],
            "links": [
                {"label": "Wikipedia", "url": prof["links"]["wikipedia"]},
                {"label": "Wikidata", "url": prof["links"]["wikidata"]},
                {"label": "Smithsonian", "url": ov["doc"]["source_url"]},
                {"label": "MusicBrainz",
                 "url": "https://musicbrainz.org/artist/90b5459b-6f1a-4dc7-a27a-9b26acda1ea3"},
            ],
        },
        "timeline": {"range": lanes["range"], "lanes": lanes["lanes"], "events": build_timeline(ov)},
        "voices": {
            "intro": f"{NUMBER_WORDS[len(voices)].capitalize()} musicians who spoke of her on tape. "
                     "Each card opens the passage in the transcript.",
            "tiers": tiers, "cards": voices,
        },
        "own": {
            "source": "Smithsonian Jazz Oral History, 1996",
            "categories": [{"key": c["key"], "label": c["label"], "count": c["liston"]}
                           for c in ov["categories"]],
            "items": own,
        },
        "discography": {"count": len(releases), "roles": role_pills, "releases": releases},
        "credits": {"portraits": sorted(credits, key=lambda c: c["name"]),
                    "covers": "Album covers from the Cover Art Archive, shown for identification."},
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                                   encoding="utf-8")

    (OUT / "transcripts.json").write_text(
        json.dumps(transcripts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if "linked-jazz-2026-transcripts" in (OUT / "data.json").read_text(encoding="utf-8"):
        sys.exit("data.json still links to the transcript reader")

    print(f"docs/data.json  {os.path.getsize(OUT / 'data.json') // 1024} KB")
    print(f"docs/transcripts.json  {os.path.getsize(OUT / 'transcripts.json') // 1024} KB  "
          f"{len(transcripts)} interviews, "
          f"{sum(len(t['blocks']) for t in transcripts.values())} turns")
    print(f"  timeline {len(data['timeline']['events'])} events "
          f"({sum(1 for e in data['timeline']['events'] if e['approx'])} undated, placed in sequence)")
    print(f"  voices {len(voices)} cards  " + "  ".join(f"{t['label']} {t['count']}" for t in tiers))
    print(f"  her words {len(own)} in {len(cats)} sections")
    print(f"  discography {len(releases)} releases, {sum(1 for r in releases if r['cover'])} with a sleeve, "
          f"{sum(1 for r in releases if not r['url'])} with no link")


if __name__ == "__main__":
    main()
