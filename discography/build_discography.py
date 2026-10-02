#!/usr/bin/env python3
"""Step 5 - assemble Melba Liston's discography and join it to the interviews.

Two things differ from the Coltrane / Davis build this was ported from.

WHAT COUNTS AS HERS. There is no "Melba Liston discography" article. Releases
come from (a) the Discography section of her biography -- every bullet, whether
or not the record has its own article -- and (b) album articles that link to her
(see harvest_discographies.py). A backlinked album is only admitted when its own
page credits her: in the Personnel section, on a track line, or in the prose.
`subject_credit` records which, and what the credit says -- trombone, arranger,
conductor, composer -- because for Liston the interesting question about a
record is very often not "did she play on it" but "did she write it".

THE JOIN RUNS BOTH WAYS. For Coltrane and Davis the payoff was "played on his
record AND talked about him". Liston was interviewed herself, so each roster
member also carries what SHE said about THEM (from liston/her_words.json):
`she_said`. Someone can be on her records, have talked about her, and have been
talked about by her.

Attribution rule for quotes about her (unchanged): a quote is attributed only
when the speaker is the interviewee and that interviewee resolves to exactly one
roster member -- by QID, or by an unambiguous name match. Documents with several
interviewees and single-token interviewee labels are left unattributed.

Writes:
  liston/discography.json            releases, with full credits
  liston/discography_personnel.json  the roster + the two-way oral-history join
  shared/discography_summary.json
"""

import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_common import parse_page  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "discography" / "raw"
LJ = "/Users/m/git/ch-jazz-mashup/linked_jazz.sqlite"

SUBJECT_QID = {"liston": "Q274146"}
SUBJECT_NAME = {"liston": "Melba Liston"}
OWN_DOC = "Liston_Melba_Interview_Transcription"

# release kind comes from the Wikidata description ("1959 studio album by ..."),
# because her article's sections say only leader / sidewoman
KIND_RULES = [
    (r"live album|recorded live|in concert|\bconcert\b|at newport|live at", "live"),
    (r"soundtrack|film score", "soundtrack"),
    (r"documentary|\bfilm\b", "film"),
    (r"compilation|box set|anthology", "compilation"),
    (r"studio album", "studio"),
    (r"\bsong\b|\bsingle\b", "single"),
]

ARRANGER = re.compile(r"arrang|conduct|orchestrat|musical director", re.I)
COMPOSER = re.compile(r"compos|written by|writer|songwrit", re.I)
PLAYER = re.compile(r"trombon|\bbone\b", re.I)
YEAR = re.compile(r"\b(19[2-9]\d|20[0-2]\d)\b")


def flags(blob, composer=False):
    return {"as_player": bool(PLAYER.search(blob)),
            "as_arranger": bool(ARRANGER.search(blob)),
            "as_composer": composer or bool(COMPOSER.search(blob))}


def classify_kind(desc, title):
    hay = f"{desc or ''} | {title}".lower()
    for pat, kind in KIND_RULES:
        if re.search(pat, hay):
            return kind
    return "album"


def subject_credit(album, page_title):
    """How does this release's own article credit Liston? -> dict.

    Order of trust: a Personnel line, then a track line, then prose. A track
    line that names her in the writer's parentheses -- '"The Moors" (Melba
    Liston)' -- is a COMPOSER credit: someone recorded her tune, which is not
    evidence she was in the studio. Prose is the weakest: the sentence may be
    about a different performance of the same music (the Zodiac Suite article
    names her for a 1957 Newport arrangement, not for the 1945 album), so prose
    credits carry needs_review and the sentences themselves.
    """
    tr = [t for t in album["tracks"] if "liston" in t.lower()]
    lines = [p for p in album["personnel"] if "liston" in p["name"].lower()]
    if lines:
        roles, notes, raws = [], [], []
        for p in lines:
            for r in p["roles"]:
                if r and r.lower() != "personnel" and r not in roles:
                    roles.append(r)
            if p.get("note") and p["note"] not in notes:
                notes.append(p["note"])
            raws.append(p["raw"])
        f = flags(" ".join(roles + notes + raws), composer=bool(tr))
        return {"found_in": "personnel", "roles": roles, "note": "; ".join(notes),
                "raw": raws, "tracks_naming_her": tr[:12], "needs_review": False, **f}
    if tr:
        return {"found_in": "tracks", "roles": ["composer"],
                "note": f"{len(tr)} of {len(album['tracks'])} track lines name her",
                "raw": tr[:12], "tracks_naming_her": tr[:12], "needs_review": False,
                "as_player": False,
                "as_arranger": bool(ARRANGER.search(" ".join(tr))), "as_composer": True}
    doc = parse_page(page_title)
    if doc and not doc.get("missing"):
        soup = BeautifulSoup(doc["html"], "lxml")
        for junk in soup.select("sup.reference, style, .navbox, .reflist, .mw-editsection"):
            junk.decompose()
        hits = []
        for el in soup.find_all(["p", "li", "td", "th"]):
            if el.find(["p", "li", "td", "ul", "table"]):
                continue
            txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", txt):
                if "Liston" in sent and sent not in hits:
                    hits.append(sent)
        if hits:
            return {"found_in": "prose", "roles": [], "note": "", "raw": [h[:500] for h in hits[:6]],
                    "tracks_naming_her": [], "needs_review": True, **flags(" ".join(hits))}
    return {"found_in": "none", "roles": [], "note": "", "raw": [], "tracks_naming_her": [],
            "needs_review": True, "as_player": False, "as_arranger": False, "as_composer": False}


def title_key(t):
    t = re.sub(r"\s*\((?:[^()]*\balbum|[^()]*\bsoundtrack)\)\s*$", "", t or "")
    return norm(t)


def load_interview_index():
    """doc_id -> {qids, labels}; and qid -> docs they were interviewed for."""
    con = sqlite3.connect(f"file:{LJ}?mode=ro", uri=True)
    docs = defaultdict(list)
    for doc_id, label, qid in con.execute(
            "select doc_id, label, qid from doc_interviewees"):
        docs[str(doc_id)].append({"label": label, "qid": qid or None})
    meta = {}
    for doc_id, title, coll, itv in con.execute(
            "select doc_id, title, collection, interviewee from documents"):
        meta[str(doc_id)] = {"title": title, "collection": coll}
        # documents.interviewee is a second, less reliable name for the same
        # person -- but it is the only place "Butter Jackson" (doc_interviewees,
        # no QID) is spelled "Quentin Jackson". Offered to the NAME matcher only,
        # as a QID-less row, so it can never override a reconciled interviewee;
        # where it is wrong (eight Rutgers docs name the interviewer, Patricia
        # Willard) it simply matches nobody on the roster.
        have = {norm(r["label"]) for r in docs[str(doc_id)]}
        if itv and norm(itv) not in have and not any(r["qid"] for r in docs[str(doc_id)]):
            docs[str(doc_id)].append({"label": itv, "qid": None})
    con.close()
    return docs, meta


def norm(s):
    """Fold a name for comparison: accents, punctuation, case."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def resolve_doc_person(rows, by_qid, by_name):
    """Which roster member is this document's interviewee? -> (key, how).

    Used for BOTH "was this person interviewed" and "did this person say
    something", so the two can never disagree -- Jimmy Owens was interviewed
    but his interviewee row carries no QID, and keying the interview list on
    QID alone left him marked as having spoken without having been interviewed.
    """
    withq = [i for i in rows if i["qid"]]
    if len(withq) == 1 and withq[0]["qid"] in by_qid:
        return by_qid[withq[0]["qid"]], "qid"
    if len(withq) > 1:
        return None, "multiple_interviewees"
    hits = set()
    for i in rows:
        n = norm(i["label"])
        if len(n.split()) < 2:      # "Jackson", "Labarbera" -- too ambiguous
            continue
        rev = " ".join(reversed(n.split()))   # surname-first documents
        for cand in (n, rev):
            if cand in by_name:
                hits.add(by_name[cand])
    if len(hits) == 1:
        return hits.pop(), "interviewee_name_match"
    return None, "interviewee_not_on_roster_or_ambiguous"


def load_quotes(subject, doc_itv, by_qid, by_name):
    """roster person_key -> the verified things that person said about him.

    Attribution is resolved against the ROSTER, not against all of Wikidata,
    because only roster members matter for this join. Two routes:

      qid   the document's single QID-bearing interviewee is on the roster.
      name  the interviewee was never reconciled to a QID (that is true of 45%
            of documents) but their name matches exactly one roster member.
            Also tries the reversed form: 13 documents store the interviewee
            surname-first ("Terry Clark" = Clark Terry).

    Single-token interviewee labels ("Jackson", "Labarbera") are refused --
    they are too collision-prone to attribute a public quote on.
    """
    said = defaultdict(lambda: {"blocks": [], "quotes": []})
    unattributed = Counter()
    methods = Counter()

    def attribute(doc_id):
        key, how = resolve_doc_person(doc_itv.get(str(doc_id), []), by_qid, by_name)
        if key:
            methods[how] += 1
        else:
            unattributed[how] += 1
        return key

    p = ROOT / subject / "enriched.json"
    if not p.exists():
        print("  (enriched.json not built yet -- the quote join is empty; re-run after "
              "extract/build_enriched.py)")
    for it in (json.loads(p.read_text(encoding="utf-8"))["items"] if p.exists() else []):
        if not it.get("is_about_subject") or it.get("speaker_role") != "interviewee":
            continue
        if it["doc_id"] == OWN_DOC:      # there the "interviewee" is Liston herself
            continue
        key = attribute(it["doc_id"])
        if not key:
            continue
        rec = said[key]
        rec["blocks"].append(it["block_id"])
        if it.get("pull_quote"):
            rec["quotes"].append({
                "block_id": it["block_id"], "quote": it["pull_quote"],
                "stance": it.get("stance"), "notable": it.get("notable") or 0,
                "summary": it.get("summary"), "source": "mention",
                "doc_id": it["doc_id"], "url": (it.get("doc") or {}).get("transcript_url"),
            })

    p = ROOT / subject / "recovered_evaluated.json"
    if p.exists():
        for it in json.loads(p.read_text(encoding="utf-8"))["items"]:
            if not it.get("is_about_subject"):
                continue
            key = attribute(it["doc_id"])
            if not key:
                continue
            rec = said[key]
            rec["blocks"].append(it["block_id"])
            if it.get("pull_quote"):
                rec["quotes"].append({
                    "block_id": it["block_id"], "quote": it["pull_quote"],
                    "stance": it.get("stance"), "notable": it.get("notable") or 0,
                    "summary": it.get("summary"), "source": "recovered",
                    "doc_id": it["doc_id"], "url": it.get("transcript_url"),
                })

    for rec in said.values():
        rec["quotes"].sort(key=lambda q: -q["notable"])
    return said, dict(unattributed), dict(methods)


def load_she_said():
    """qid / normalised name -> what Liston said about that person (her_words.json)."""
    p = ROOT / "liston" / "her_words.json"
    by_qid, by_name = {}, {}
    if not p.exists():
        return by_qid, by_name, False
    for it in json.loads(p.read_text(encoding="utf-8"))["items"]:
        if not it.get("is_person"):
            continue
        rec = {
            "relation": it.get("relation"), "direction": it.get("direction"),
            "basis": it.get("basis"), "tie": it.get("tie") or [],
            "summary": it.get("summary"), "one_liner": it.get("one_liner"),
            "her_quote": it.get("her_quote"), "her_quote_block_id": it.get("her_quote_block_id"),
            "bryant_quote": it.get("bryant_quote"),
            "notable": it.get("notable") or 0,
            "url": it.get("her_quote_url") or it.get("url"),
        }
        if it.get("qid"):
            by_qid[it["qid"]] = rec
        n = norm(it.get("name") or "")
        if len(n.split()) >= 2:
            by_name[n] = rec
    return by_qid, by_name, True


def main():
    subject, qid_subj = "liston", SUBJECT_QID["liston"]
    albums = json.loads((RAW / "albums.json").read_text(encoding="utf-8"))["albums"]
    ents = json.loads((RAW / "entities.json").read_text(encoding="utf-8"))["entities"]
    people = json.loads((RAW / "personnel_resolved.json").read_text(
        encoding="utf-8"))["people"]
    rows = json.loads((RAW / "liston_rows.json").read_text(encoding="utf-8"))["rows"]
    doc_itv, doc_meta = load_interview_index()

    # ---- which release articles, and how each was found
    found = {}     # canonical article title -> {sources, bullets}
    for v in ents.values():
        if v["bucket"] != "release":
            continue
        m = found.setdefault(v["title"], {"sources": set(), "bullets": []})
        for sn in v["seen_in"]:
            # in a discography bullet only the italic link is the record; the
            # other links on the line are the leader
            if sn.get("source") == "discography_section" and not sn.get("italic"):
                continue
            m["sources"].add(sn.get("source") or "discography_section")
            if sn.get("source") == "discography_section":
                m["bullets"].append(sn)

    releases, rejected = [], []
    for title, m in sorted(found.items()):
        a = albums.get(title)
        if not a:
            continue
        info = a["infobox"]
        credit = subject_credit(a, title)
        listed = "discography_section" in m["sources"]
        if not listed and credit["found_in"] == "none":
            rejected.append({"title": title, "qid": a["qid"],
                             "reason": "links to her article but its own page does not credit her"})
            continue
        b = m["bullets"][0] if m["bullets"] else {}
        section = b.get("section") or ""
        if listed and re.search(r"leader", section, re.I):
            role = "leader"
        elif credit["roles"] and all(r.lower() == "cast" for r in credit["roles"]):
            role = "appears_on_screen"      # archival footage in a documentary
        elif credit["as_player"]:
            role = "sidewoman"
        elif credit["as_arranger"]:
            role = "arranger"
        elif credit["as_composer"]:
            role = "composer"
        elif listed:
            role = "sidewoman"       # her article files it under "As sidewoman or guest"
        else:
            role = "mentioned"
        year = (b.get("year")
                or next((d[:4] for d in a["publication_dates"] if d[:4].isdigit() and d[:4] != "0000"), None)
                or next(iter(YEAR.findall((info.get("released") or {}).get("text") or "")), None)
                or next(iter(YEAR.findall((info.get("recorded") or {}).get("text") or "")), None)
                or next(iter(YEAR.findall(a["description"] or "")), None))
        releases.append({
            "title": title,
            "qid": a["qid"],
            "has_article": True,
            "kind": classify_kind(a["description"], title),
            "subject_role": role,
            "subject_credit": credit,
            "listed_in_her_discography": listed,
            "found_via": sorted(m["sources"]),
            "leader": b.get("leader_text"),
            "year": year,
            "sections": sorted({x.get("section") for x in m["bullets"] if x.get("section")}),
            "wikipedia_url": a["wikipedia_url"],
            "wikidata_url": a["wikidata_url"],
            "description": a["description"],
            "released": (info.get("released") or {}).get("text"),
            "recorded": (info.get("recorded") or {}).get("text"),
            "studio": (info.get("studio") or {}).get("text"),
            "venue": (info.get("venue") or {}).get("text"),
            "label": (info.get("label") or {}).get("text") or b.get("label_text"),
            "genre": (info.get("genre") or {}).get("text"),
            "length": (info.get("length") or {}).get("text"),
            "producer": (info.get("producer") or {}).get("text"),
            "publication_dates": a["publication_dates"],
            "musicbrainz": a["musicbrainz"],
            "image": a["image"],
            "discography_row": b.get("row_text") or "",
            "track_count": len(a["tracks"]),
            "tracks": a["tracks"],
            "personnel_count": a["personnel_count"],
            "personnel": [{
                "name": p["name"], "person_key": p.get("person_key"),
                "qid": p.get("person_qid"), "identified_via": p.get("identified_via"),
                "roles": p["roles"], "note": p["note"],
                "credit_type": p["credit_type"], "group": p["group"],
            } for p in a["personnel"]],
            "session_notes": a["session_notes"],
        })

    # ---- prose-only and uncredited releases, as judged by a reader
    # (discography/raw/credit_review_output.json -- an Opus subagent given the
    # album page's own sentences; see the README). "no" = she is only mentioned
    # there, so the release leaves the discography; "yes" = the prose is a real
    # credit; "unverified" = her biography lists it, the album page is silent.
    mentioned_only = []
    rp = RAW / "credit_review_output.json"
    if rp.exists():
        rv = json.loads(rp.read_text(encoding="utf-8"))
        verdict = {i["title"]: i for i in rv["items"]}
        keep = []
        for rel in releases:
            v = verdict.get(rel["title"])
            if v is None:
                keep.append(rel)
                continue
            c = rel["subject_credit"]
            c["review"] = {k: v.get(k) for k in ("credited_on_this_release", "role", "scope",
                                                  "evidence", "reasoning", "confidence")}
            c["review"]["judged_by"] = rv.get("judged_by")
            if v["credited_on_this_release"] == "no":
                mentioned_only.append({"title": rel["title"], "qid": rel["qid"], "year": rel["year"],
                                       "wikipedia_url": rel["wikipedia_url"],
                                       "reason": v["reasoning"], "evidence": v["evidence"]})
                continue
            if v["credited_on_this_release"] == "yes":
                c["needs_review"] = False
                role = v["role"]
                c["as_arranger"] = role in ("arranger", "conductor", "arranger_and_player")
                c["as_player"] = role in ("sidewoman", "arranger_and_player")
                c["as_composer"] = role == "composer"
                c["note"] = v.get("scope") or c["note"]
                rel["subject_role"] = {"arranger_and_player": "sidewoman",
                                       "conductor": "arranger"}.get(role, role)
            else:   # unverified: keep where her biography files it, and say so
                c["needs_review"] = True
                c["as_arranger"] = c["as_player"] = c["as_composer"] = False
                rel["subject_role"] = "listed_unverified"
            keep.append(rel)
        releases = keep

    # ---- discography bullets whose record has no article of its own
    release_titles = {v["requested_title"] for v in ents.values() if v["bucket"] == "release"}
    by_key = {}
    for rel in releases:
        by_key.setdefault(title_key(rel["title"]), rel)
    unlinked, merged_bullets = [], 0
    for r in rows:
        if r.get("source") != "discography_section":
            continue
        links = [l for c in r["cells"] for l in c["links"]]
        if any(l["italic"] and l["title"] in release_titles for l in links):
            continue
        # the bullet is plain text on her page, but the record may still have an
        # article that the backlink sweep found ("Plays Hip Hits" is the article
        # "Quincy Jones Plays Hip Hits"): fold the bullet into it
        k = norm(r["title_text"] or "")
        hit = by_key.get(k) or next(
            (rel for kk, rel in by_key.items()
             if k and len(k.split()) >= 2 and (kk.endswith(" " + k) or kk.startswith(k + " "))), None)
        if hit is not None:
            hit["listed_in_her_discography"] = True
            hit["found_via"] = sorted(set(hit["found_via"]) | {"discography_section"})
            hit["leader"] = hit["leader"] or r["leader_text"]
            hit["year"] = r["year"] or hit["year"]
            hit["discography_row"] = hit["discography_row"] or r["text"]
            hit["sections"] = sorted(set(hit["sections"]) | {r["section"]})
            if hit["subject_role"] in ("mentioned", "composer") and not hit["subject_credit"]["as_arranger"]:
                hit["subject_role"] = "sidewoman"
            merged_bullets += 1
            continue
        leaders = [l["title"] for l in links if not l["italic"]]
        unlinked.append({
            "title": r["title_text"] or r["text"],
            "qid": None, "has_article": False, "kind": "album",
            "subject_role": "leader" if re.search(r"leader", r["section"], re.I) else "sidewoman",
            "subject_credit": {"found_in": "her_discography_list_only", "roles": [], "note": "",
                               "raw": [r["text"]], "tracks_naming_her": [], "needs_review": False,
                               "as_arranger": False, "as_player": False, "as_composer": False},
            "listed_in_her_discography": True, "found_via": ["discography_section"],
            "leader": r["leader_text"], "leader_articles": leaders,
            "year": r["year"], "sections": [r["section"]],
            "wikipedia_url": None, "wikidata_url": None, "description": None,
            "released": r["year"], "recorded": None, "studio": None, "venue": None,
            "label": r["label_text"], "genre": None, "length": None, "producer": None,
            "publication_dates": [], "musicbrainz": None, "image": None,
            "discography_row": r["text"], "track_count": 0, "tracks": [],
            "personnel_count": 0, "personnel": [], "session_notes": [],
        })
    releases += unlinked
    releases.sort(key=lambda r: (r["year"] or "9999", r["title"]))

    # ---- roster: everyone credited on the releases with an article
    wanted = {r["title"] for r in releases if r["has_article"]}
    members = {key: e for key, e in people.items()
               if e.get("qid") != qid_subj
               and any(c["album"] in wanted for c in e["credits"])}
    by_qid = {e["qid"]: key for key, e in members.items() if e["qid"]}
    by_name = {}
    for key, e in members.items():
        for v in [e["name"], *e["name_variants"]]:
            n = norm(v)
            if len(n.split()) >= 2:
                by_name[n] = None if n in by_name and by_name[n] != key else key
    by_name = {k: v for k, v in by_name.items() if v}

    said, unattributed, methods = load_quotes(subject, doc_itv, by_qid, by_name)
    she_qid, she_name, have_she = load_she_said()

    itv_by_key = defaultdict(list)
    for doc_id, rws in doc_itv.items():
        if doc_id == OWN_DOC:
            continue
        key, how = resolve_doc_person(rws, by_qid, by_name)
        if key:
            itv_by_key[key].append({
                "doc_id": doc_id, "matched_via": how,
                "label": rws[0]["label"] if rws else None,
                **doc_meta.get(doc_id, {})})

    roster = []
    for key, e in members.items():
        creds = [c for c in e["credits"] if c["album"] in wanted]
        itv = itv_by_key.get(key, [])
        spoke = said.get(key)
        she = she_qid.get(e["qid"]) if e["qid"] else None
        if she is None:
            for v in [e["name"], *e["name_variants"]]:
                she = she_name.get(norm(v))
                if she:
                    break
        roster.append({
            "person_key": key,
            "qid": e["qid"],
            "name": e["name"],
            "identified_via": e["identified_via"],
            "description": e["description"],
            "wikipedia": e["wikipedia"],
            "birth": e["birth"], "death": e["death"], "image": e["image"],
            "name_variants": e["name_variants"],
            "instruments": sorted({r for c in creds for r in c["roles"]}),
            "album_count": len({c["album"] for c in creds}),
            "albums": sorted({c["album"] for c in creds}),
            "credit_type": "musician" if any(
                c["credit_type"] == "musician" for c in creds) else "technical",
            # ---- the oral-history join, both directions ----
            "interviewed_in_corpus": bool(itv),
            "interviews": itv,
            "said_about_subject": bool(spoke),
            "blocks_about_subject": len(spoke["blocks"]) if spoke else 0,
            "quotes": (spoke["quotes"][:8] if spoke else []),
            "she_spoke_of_them": bool(she),
            "she_said": she,
        })
    roster.sort(key=lambda p: (-p["blocks_about_subject"], -bool(p["she_spoke_of_them"]),
                               -p["album_count"], p["name"]))

    played_and_spoke = [p for p in roster if p["said_about_subject"]]
    played_and_interviewed = [p for p in roster if p["interviewed_in_corpus"]]
    bandmates_spoke = [p for p in played_and_spoke if p["credit_type"] == "musician"]
    writers_spoke = [p for p in played_and_spoke if p["credit_type"] == "technical"]
    she_spoke = [p for p in roster if p["she_spoke_of_them"]]
    both_ways = [p for p in roster if p["she_spoke_of_them"] and p["said_about_subject"]]

    with_article = [r for r in releases if r["has_article"]]
    stats = {
        "releases": len(releases),
        "releases_with_article": len(with_article),
        "releases_listed_without_article": len(unlinked),
        "from_her_discography_section": sum(1 for r in releases if r["listed_in_her_discography"]),
        "found_only_by_backlink": sum(1 for r in releases if not r["listed_in_her_discography"]),
        "backlinked_releases_rejected_no_credit": len(rejected),
        "releases_where_she_is_only_mentioned": [m["title"] for m in mentioned_only],
        "by_kind": dict(Counter(r["kind"] for r in releases)),
        "by_subject_role": dict(Counter(r["subject_role"] for r in releases)),
        "credit_found_in": dict(Counter(r["subject_credit"]["found_in"] for r in releases)),
        "credited_as_arranger_or_conductor": sum(
            1 for r in releases if r["subject_credit"]["as_arranger"]),
        "credited_as_composer": sum(1 for r in releases if r["subject_credit"]["as_composer"]),
        "credits_needing_review": sorted(r["title"] for r in releases
                                         if r["subject_credit"]["needs_review"]),
        "unlinked_bullets_merged_into_articles": merged_bullets,
        "credited_as_player": sum(1 for r in releases if r["subject_credit"]["as_player"]),
        "credited_as_both": sum(1 for r in releases if r["subject_credit"]["as_arranger"]
                                and r["subject_credit"]["as_player"]),
        "total_credits": sum(r["personnel_count"] for r in releases),
        "roster_size": len(roster),
        "roster_with_qid": sum(1 for p in roster if p["qid"]),
        "roster_interviewed_in_corpus": len(played_and_interviewed),
        "roster_who_spoke_about_subject": len(played_and_spoke),
        "musicians_who_played_and_spoke": len(bandmates_spoke),
        "critics_producers_who_were_credited_and_spoke": len(writers_spoke),
        "critics_producers_named": sorted(p["name"] for p in writers_spoke),
        "her_words_available": have_she,
        "roster_she_spoke_of": len(she_spoke),
        "roster_both_directions": len(both_ways),
        "roster_both_directions_named": sorted(p["name"] for p in both_ways),
        "quote_blocks_from_credited_people": sum(p["blocks_about_subject"] for p in roster),
        "quote_blocks_from_musicians": sum(p["blocks_about_subject"] for p in bandmates_spoke),
        "attribution_methods": methods,
        "unattributed_quote_blocks": unattributed,
    }

    base = {"subject": subject, "subject_qid": qid_subj,
            "subject_name": SUBJECT_NAME[subject],
            "source": "en.wikipedia.org 'Melba Liston' (Discography section) + album "
                      "articles that link to her; entities typed against Wikidata"}
    (ROOT / subject / "discography.json").write_text(
        json.dumps({**base, "count": len(releases), "stats": stats,
                    "rejected_backlinks": rejected,
                    "mentioned_only": mentioned_only,
                    "releases": releases}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (ROOT / subject / "discography_personnel.json").write_text(
        json.dumps({**base, "count": len(roster),
                    "join_rule": "quote attributed only when the speaker is "
                                 "the interviewee and the document has exactly "
                                 "one QID-bearing interviewee; she_said is joined by "
                                 "QID, else by an exact normalised full-name match",
                    "stats": stats, "people": roster},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== {subject} ===")
    print(f" releases {len(releases)}  ({len(with_article)} with an article, "
          f"{len(unlinked)} listed without one; {stats['found_only_by_backlink']} found only "
          f"by backlink; {len(rejected)} backlinked albums rejected)")
    print(f" kinds {stats['by_kind']}")
    print(f" her role {stats['by_subject_role']}   credit found in {stats['credit_found_in']}")
    print(f" as arranger/conductor {stats['credited_as_arranger_or_conductor']}"
          f"   as composer {stats['credited_as_composer']}"
          f"   as player {stats['credited_as_player']}   player+arranger {stats['credited_as_both']}")
    print(f" needs review: {stats['credits_needing_review']}")
    print(f" credits {stats['total_credits']}  roster {len(roster)} "
          f"({stats['roster_with_qid']} with QID)")
    print(f" credited on a record with her AND interviewed in the corpus: "
          f"{len(played_and_interviewed)}")
    print(f" ... AND said something about her on the record: {len(played_and_spoke)}  "
          f"({len(bandmates_spoke)} musicians, {len(writers_spoke)} critics/producers)")
    print(f" she spoke of them: {len(she_spoke)}   both directions: {len(both_ways)} "
          f"{stats['roster_both_directions_named']}")
    print(f" attribution: {methods}")
    print(f" unattributed: {unattributed}")
    print(" top musician-witnesses:")
    for p in bandmates_spoke[:12]:
        print(f"   {p['blocks_about_subject']:3} blocks / {p['album_count']:3} albums  "
              f"{p['name'][:28]:30} {p['qid']}")
    if rejected:
        print(" rejected backlinks:", [r["title"] for r in rejected])

    (ROOT / "shared").mkdir(exist_ok=True)
    (ROOT / "shared" / "discography_summary.json").write_text(
        json.dumps({subject: stats}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
