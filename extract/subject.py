#!/usr/bin/env python3
"""The one subject of this repo, and the two things that make her different
from the Coltrane / Davis build this pipeline was ported from.

1. SHE WAS INTERVIEWED. Coltrane and Davis never sat for an oral history in
   this corpus; Melba Liston did (Smithsonian, 4-5 December 1996, interviewed
   by the trumpeter Clora Bryant). So `OWN_DOC` exists, and every script has to
   decide what a "mention" inside her own interview means. The rule used
   everywhere: blocks from OWN_DOC are kept but flagged `own_interview`, and are
   never counted as "another musician talking about her" unless the speaker is
   Clora Bryant -- who is a peer and a friend, not a neutral archivist.

2. SHE IS THINLY RECONCILED. Only 41 blocks outside her own interview resolve
   to her QID, and the person layer left real mentions on the floor: a bare
   "Melba" in the Quincy Jones, Mary Lou Williams and Von Freeman interviews,
   "Liston, Melba" in Shirley Horn's, "Melvin Liston" in J.C. Higginbotham's.
   With so few mentions each one matters, so `target_blocks()` adds those back
   as `fts_supplement` candidates. They are candidates: the evaluation pass
   decides whether each one is really her.
"""

import re

DB = "/Users/m/git/ch-jazz-mashup/linked_jazz.sqlite"
ROOT = "/Users/m/git/liston-centennial-2026"

KEY = "liston"
QID = "Q274146"
NODE_ID = "wd:Q274146"
NAME = "Melba Liston"
OWN_DOC = "Liston_Melba_Interview_Transcription"

# her interviewer, who is herself a musician in the corpus
INTERVIEWER = {"name": "Clora Bryant", "speaker_label": "Bryant", "qid": "Q1102326"}

SUBJECTS = {KEY: QID}

# A text hit that the person layer did not link to her QID. Deliberately
# narrow: "Liston" alone is Sonny Liston, Lonnie Liston Smith, Cal Liston and
# Liston Johnson far more often than it is her.
SUPPLEMENT_RE = re.compile(
    r"\bMelba\s+Liston\b|\bListon,\s*Melba\b|\bMelvin\s+Liston\b|\bMelba\b(?!\s+Moore)"
)


def person_layer_blocks(con):
    """block_id -> list of mention dicts, from the QID-reconciled person layer."""
    out = {}
    for r in con.execute(
        """SELECT p.person_id, p.doc_id, p.canonical, p.count AS person_count,
                  p.confidence, p.surface_forms, pm.block_id, pm.start, pm.end
             FROM persons p JOIN person_mentions pm USING(person_id)
            WHERE p.qid = ? AND pm.block_id IS NOT NULL""",
        (QID,),
    ):
        out.setdefault(r["block_id"], []).append(dict(r))
    return out


def supplement_blocks(con, known):
    """block_id -> list of pseudo-mention dicts for text hits outside `known`.

    Never looks inside OWN_DOC: there the person layer is complete enough and a
    bare "Melba" is always her.
    """
    import json

    out = {}
    rows = con.execute(
        """SELECT b.block_id, b.doc_id, b.text
             FROM blocks_fts JOIN blocks b ON b.block_id = blocks_fts.rowid
            WHERE blocks_fts MATCH 'Melba OR Liston' AND b.doc_id != ?""",
        (OWN_DOC,),
    ).fetchall()
    per_doc = {}
    for r in rows:
        if r["block_id"] in known:
            continue
        hits = list(SUPPLEMENT_RE.finditer(r["text"] or ""))
        if not hits:
            continue
        per_doc.setdefault(r["doc_id"], []).append((r["block_id"], hits))
    for doc_id, blks in per_doc.items():
        forms = sorted({m.group(0) for _, hits in blks for m in hits})
        n = sum(len(hits) for _, hits in blks)
        for block_id, hits in blks:
            out[block_id] = [
                {
                    "person_id": None,
                    "doc_id": doc_id,
                    "canonical": "Melba Liston (unreconciled text hit)",
                    "person_count": n,
                    "confidence": None,
                    "surface_forms": json.dumps(forms, ensure_ascii=False),
                    "block_id": block_id,
                    "start": m.start(),
                    "end": m.end(),
                }
                for m in hits
            ]
    return out


def target_blocks(con):
    """Every block that may be about her: block_id -> (mentions, source)."""
    pl = person_layer_blocks(con)
    out = {bid: (ms, "person_layer") for bid, ms in pl.items()}
    for bid, ms in supplement_blocks(con, set(pl)).items():
        out[bid] = (ms, "fts_supplement")
    return out
