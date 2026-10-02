# Shared extraction spec — Melba Liston centennial data build

Ported from the Coltrane / Davis centennial build
(`~/git/linked-jazz-coltrane-davis`). Same corpus, same conventions, one subject.

## Source
Read-only SQLite: `/Users/m/git/ch-jazz-mashup/linked_jazz.sqlite`
Schema doc: `/Users/m/git/ch-jazz-mashup/SQLITE.md` (READ IT FIRST)
Never write to the DB. Open read-only (`file:...?mode=ro`).

## Subject
| key | person | QID | node_id | community |
|---|---|---|---|---|
| `liston` | Melba Liston (13 Jan 1926 – 23 Apr 1999), trombonist, arranger, composer | `Q274146` | `wd:Q274146` | 2 |

All of this lives in `extract/subject.py`; import it rather than repeating it.

**She is an interviewee.** `OWN_DOC = Liston_Melba_Interview_Transcription`
(Smithsonian Jazz Oral History, 4–5 Dec 1996, interviewer Clora Bryant
`Q1102326`). Every script must decide what it does with that document; the
default is: keep its blocks, flag them `own_interview`, and never count them as
"another musician talking about her".

**This phase = data only, no HTML.**

## Output layout
```
liston/<file>.json      everything about the subject
shared/<file>.json      cross-cutting: images, communities, summaries
extract/<script>.py     transcript-derived layers  (stdlib only)
discography/<script>.py Wikipedia / Wikidata / Commons layers (bs4 + lxml)
img/                    local copies of portraits and sleeves
```
Run anything with `uv run python <script>` from the repo root.

## Universal JSON conventions
- UTF-8, `json.dump(..., ensure_ascii=False, indent=1)`.
- Every top-level file is an object with
  `{"subject": "liston", "qid": "Q274146", "generated_from": "...", "count": <n>, "items": [...]}`
  plus task-specific keys.
- Any record derived from a transcript block carries provenance: `doc_id`,
  `block_id`, `page`, `block`, and a deep link
  `<documents.transcript_url>#b<page>-<block>`.
- Network deep link: `https://thisismattmiller.github.io/linked-jazz-2026-network/#<node_id>`
- Sort `items` by descending significance so a page can take top-N.
- Text is verbatim from the DB. Only runs of whitespace are collapsed; the raw
  form is kept in `text_raw` when that changed anything.

## Identity rule
Resolve people via `persons.qid` / `nodes.qid`, not by raw text search — with one
deliberate exception. Only ~40 blocks outside her own interview reconcile to her
QID, and the person layer left real mentions behind (a bare "Melba", "Liston,
Melba", "Melvin Liston"). `subject.target_blocks()` adds those back as
`mention_source: "fts_supplement"`; they are candidates until the evaluation
pass confirms each one.

## Judgement
Anything that requires reading and deciding — is this block about her, what did
she say about this person, which quote leads — is done by **Claude Opus
subagents** working to a written spec in this directory (`EVAL_SPEC.md`,
`RECOVERED_SPEC.md`, `HER_WORDS_SPEC.md`, `OWN_VOICE_SPEC.md`,
`WITNESS_SPEC.md`). The scripts package the inputs and merge the outputs; every
merge re-verifies every quote as an exact substring of its source block and
drops what fails.

## Style
Fail loudly on schema surprises. Print a short summary at the end of each script.
