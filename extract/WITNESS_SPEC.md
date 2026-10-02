# Witness spec — how each person knew Melba Liston

Project root: `/Users/m/git/liston-centennial-2026`

A centennial web page about **Melba Liston** (trombonist, arranger, composer;
1926–1999) will show, for each musician who spoke about her in an oral-history
interview, one row: *who they are — how they knew her — their best line*.

An earlier pass judged individual transcript blocks. Your job is the step from
blocks to **people**: for each witness, read everything they said about her and
decide what their relation to her actually was, which line should lead, and the
short phrase that says how they knew her.

## Input — `liston/witness_input.json`

`items[]`, one per witness. A witness is one interview document:

```
witness_key          copy it through
doc                  the interview: title, collection, year, interviewee, interviewer
interviewees[]       who was interviewed (label, qid, description, dates)
is_her_interviewer   present and true only for Clora Bryant (see below)
upstream_relations[] what an earlier, weaker model decided -- a lead, NOT a finding.
                     Often "knows of", often inferred from the INTERVIEWER's words.
                     Empty for witnesses that model never saw.
blocks[]             every block judged to be about her, in reading order:
    block_id, kind (mention | recovered_answer | recovered_continuation | bryant_testimony)
    speaker, speaker_role (interviewee | interviewer | unknown | null)
    mention_kind, notable, stance, summary, pull_quote, notes   <- the block-level judgement
    context_before[]   up to 4 preceding turns
    text               THE block
    context_after[]    up to 4 following turns
```

Read every block of a witness, with its context, before judging that witness.

**Clora Bryant** is a special witness. She is the trumpeter who *interviewed*
Liston in 1996; she was a Los Angeles contemporary and friend. Her blocks are
things she said to Liston, in the second person, inside Liston's own interview.
Judge her as a witness like any other — the speaker is Bryant.

## Output — `liston/witness_output.json`

```json
{"subject": "liston", "count": <n>, "items": [ ...one per input item, same order... ]}
```

Each item (values below are invented, to show shape):

```json
{
 "witness_key": "123456",
 "speaker_name": "Jane Example",
 "speaker_qid": "Q1",
 "spoke_themselves": true,
 "relation": "in music group with",
 "direction": "mutual",
 "contact_level": "worked_together",
 "basis": ["direct_contact"],
 "context": "Dizzy Gillespie big band, 1956–57",
 "one_liner": "sat beside her in the trombone section",
 "summary": "Example recalled sharing a section with Liston and said she wrote the band's best charts.",
 "lead_block_id": 200001,
 "lead_quote": "exact contiguous substring of that block's text",
 "second_block_id": 200009,
 "second_quote": "exact contiguous substring, or null",
 "stance": "positive",
 "stance_strength": 2,
 "notable": 2,
 "upstream_relation_ok": false,
 "caution": "",
 "confidence": "high",
 "notes": ""
}
```

### Field definitions

**`speaker_name`** / **`speaker_qid`** — who is actually talking about her. For a
single-interviewee document this is that interviewee (copy `label` and `qid`;
fix an obviously inverted name such as "Akiyoshi Toshiko" → "Toshiko Akiyoshi",
"HANK JONES" → "Hank Jones"). For a joint interview, decide from the blocks'
speakers which interviewee speaks of her; if it is not determinable, say so in
`notes` and use the document's first interviewee. `speaker_qid` is `null` when
the input gives none — **never invent a QID**.

**`spoke_themselves`** (bool) — did the witness say anything about her in their
**own** words? `false` when she appears only in the interviewer's question, an
editor's bracket, or the archive's front matter, and the witness merely assents
("Yeah.") or says nothing. A `false` here means the witness is not really a
witness; set `relation` from what little is established (often `knows of` or
`none`), `notable: 0` or `1`, and `lead_quote: null` unless the interviewer's
line plus the assent is itself worth showing (then quote the witness's own
words only).

**`relation`** — the witness's relation to Liston. One of:
`in music group with` · `collaborated with` · `played with` · `toured with` ·
`played under` · `mentor of` · `influenced by` · `friend of` · `acquaintance of`
· `has met` · `knows of` · `none`.

Pick the **strongest relation the testimony actually supports**. Do not use
outside biographical knowledge to upgrade: Randy Weston's forty-year partnership
with her is `collaborated with` because *he describes it*, not because it is
famous. If the witness only saw her play, that is `knows of`. A claim of contact
needs the witness to state contact.

**`direction`** — for `played under`, `mentor of`, `influenced by`:
`liston_leads` (she was the leader / musical director / teacher / influence) or
`witness_leads` (the witness was). Otherwise `mutual`, or `na` for `knows of` /
`none`. Musical director of a band counts as leading the players in it only if
the witness presents it that way.

**`contact_level`** — `worked_together` | `knew_personally` | `met_briefly` |
`same_scene` | `no_contact` | `unclear`.

**`basis`** — how the witness knows of her at all; every one that applies:
`direct_contact`, `saw_live`, `recordings`, `reputation`, `press_or_study`,
`shared_associates`, `none_evident`.

**`context`** — the band, record, place or period the connection belongs to, **as
the testimony gives it** ("Quincy Jones band, Europe, c.1960"), or `""`.

**`one_liner`** — the caption phrase: **3 to 8 words, lower case, no final
period**, starting with a verb or preposition, referring to Liston as "her" /
"she", never by name. Rules, the first absolute:
1. Use ONLY facts stated in this witness's blocks. No place, band, club, record,
   instrument, year or person may appear unless the testimony contains it. A dull
   true phrase beats a vivid invented one.
2. Do NOT restate the relation label — the page prints it beside the phrase.
   Bad: "was a friend of hers". Good: "roomed next door to her on the Basie tour"
   (if that is what was said).
3. If nothing specific is supported, return `""`.

**`summary`** — ONE sentence, past tense, naming the witness by surname: the gist
of everything they said about her.

**`lead_block_id`** / **`lead_quote`** — the single best thing this witness said
about her, for display beside their name. `lead_quote` MUST be an exact,
contiguous substring of the `text` of the block `lead_block_id` (one of this
witness's `blocks[]`), and must be the **witness's own words** — not the
interviewer's, and not a bracketed editorial insertion standing alone. You may
improve on the block-level `pull_quote` (shorter, cleaner, a better sentence) as
long as it stays an exact substring. `null` / `null` if the witness said nothing
quotable.

**`second_block_id`** / **`second_quote`** — a second, different line worth
showing, same rules, from a different sentence (same or another block). `null`
if none.

**`stance`** — `positive` | `negative` | `mixed` | `neutral` — the witness's
attitude to Liston across all their blocks. **`stance_strength`** 0–3.

**`notable`** 0–3 — how good is this witness's row for the page, taken as a
whole? `3` = a first-hand witness with a line you would print large (**at most
6**). `2` = a real connection and a usable quote. `1` = thin but genuine. `0` =
nothing usable / not really a witness.

**`upstream_relation_ok`** (bool or null) — was the earlier model's relation
right? `null` when `upstream_relations` is empty.

**`caution`** — anything that should stop a line being displayed unqualified: a
factual claim that is probably wrong (say what and why you doubt it), a quote
that reads misleadingly out of context, a remark set inside a passage a reader
could find offensive, an uncertain identification (e.g. a name the transcript
garbles). `""` if none. This field is read by a human before publication.

**`confidence`** — `high` | `medium` | `low`. **`notes`** — anything else.

## Rules

- **Never invent text.** Quotes are exact substrings of one block's `text`.
- **Only the testimony decides.** Outside knowledge may be used to recognise a
  name, a band or a record and to fix the spelling of the witness's own name —
  never to supply a fact about the relationship.
- Do not fix or tidy transcript text inside a quote.
- Exactly one output item per input item, same order, `witness_key` copied.
- Output valid JSON, UTF-8, `ensure_ascii=False`, written with a short Python
  script run via `uv run --python 3.14 python <script>`. Helper scripts go in
  the scratchpad directory you were given. Write nothing inside the project
  except `liston/witness_output.json`. Do not run git commands.
- **Write incrementally** — rewrite the output file after every 8 witnesses, and
  resume from an existing file if there is one.
- **Validate before finishing**: output parses; count and `witness_key` order
  match the input; every non-null `lead_quote` / `second_quote` is an exact
  substring of the `text` of the named block, and that block belongs to that
  witness; every `one_liner` is ≤ 8 words, lower case, with no final period;
  `relation`, `direction`, `contact_level`, `basis` use only the allowed values;
  at most 6 items have `notable == 3`.
