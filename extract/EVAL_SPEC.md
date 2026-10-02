# Evaluation spec — classifying what was said about Melba Liston

You are judging **what a jazz musician actually said** about **Melba Liston**
(trombonist, arranger, composer; 13 January 1926 – 23 April 1999) in an
oral-history interview, for a centennial web page.

*(Ported from the Coltrane / Davis centennial build, v2. The method is the same;
the traps are hers.)*

Project root: `/Users/m/git/liston-centennial-2026`

## Your input

One chunk file: `liston/eval_input/chunk_NNN.json`.
Each item is one transcript block that mentions the subject, wrapped in an
expanded window:

```
context_before[]  ~4-8 preceding blocks (~1200-4000 chars)
target            THE block that mentions the subject
context_after[]   2-4 blocks, or 6-8 when the interviewer is speaking
doc               title, collection, year, interviewee(s), interviewer, deep link
subject_surface_forms      the name variants this interview used for the subject
speaker_role               interviewee | interviewer | unknown (pre-computed, imperfect)
target_starts_midsentence  target begins lowercase — it is a page-break continuation
target_ends_midsentence    target has no terminal punctuation — it continues below
own_interview              true = this block is from LISTON'S OWN interview (see below)
mention_source             person_layer | fts_supplement (see trap 1)
```

**Read the whole window before judging.** The single most common failure is
reading `target` alone.

## Two kinds of chunk

The chunk's top-level `own_interview` flag tells you which you have.

### A. Other people's interviews (`own_interview: false`)

The ordinary case: some other musician's oral history, in which Liston comes up.
There are only ~50 of these blocks in the entire 1,347-interview corpus, so each
one is a tenth of a witness. Be exact.

### B. Her own interview (`own_interview: true`)

Liston was interviewed for the Smithsonian Jazz Oral History Program on 4–5
December 1996 at her home in Los Angeles. Two things make this document unlike
any other:

- **The interviewer is a peer.** Speaker `Bryant` is **Clora Bryant**
  (1927–2019), a trumpeter who came up in Los Angeles alongside Liston and knew
  her for decades. When Bryant tells Liston to her face *"that is one of the
  most beautiful things you've ever done"* or *"you've been a guiding light for a
  lot of people, including me"*, that is a musician's first-hand testimony about
  the subject, addressed in the second person. It is **not** an
  `interviewer_question`. Use `mention_kind: "peer_interviewer_testimony"` and
  score it like any other musician's comment (`relationship: "personally"`,
  `notable` up to 3). A plain question that merely addresses her by name
  (*"Melba, who was your main influence?"*) is still `interviewer_question`,
  capped at `notable: 1`.
- **Square brackets are the transcriber, not the speaker.** The interview was
  recorded eleven years after Liston's 1985 stroke; she had memory loss and
  difficulty speaking, and the transcriber replaced stretches of it with
  bracketed summaries: *"[Liston cannot recall what happened next.]"*,
  *"[asks about Liston starting music at the age of 3 or 4.]"*. A block whose
  only mention of her is inside such a bracket is `transcriber_summary`
  (`notable: 0`, no `pull_quote`). **Never put bracketed text in a
  `pull_quote`.**
- When the speaker is `Liston` herself and her name appears because she is
  reporting what someone said to her (*Gerald said, "Melba, write something up
  and do it."*), use `mention_kind: "self_account"`, set
  `quotes_the_subject: false`, `relationship: "not_applicable"`, and judge
  `notable` on how good the line is as *her own voice*. These are gold of a
  different kind — say what the reported speaker said in `summary`.

## Known traps

1. **`mention_source: "fts_supplement"` means identity is UNVERIFIED.** The
   reconciled person layer linked only ~40 blocks outside her own interview to
   her, so a text search added the blocks it missed: a bare **"Melba"**,
   **"Liston, Melba"**, **"Melvin Liston"**. Decide from the window whether each
   is really her, using only what the window gives you (who else is named, the
   band, the instrument, the era). Say how sure you are in `confidence`. If you
   cannot tell, `is_about_subject: false`, `confidence: "low"`, and explain.
2. **Other Listons and other Melbas exist in this corpus**: boxer **Sonny
   Liston**, keyboardist **Lonnie Liston Smith**, **Cal Liston** (a Dallas dance
   hall operator), New Orleans musician **Liston Johnson**, singer **Melba
   Moore**. Any of these is a `false_positive`.
3. **The editor supplied the name, not the speaker.** Rutgers transcripts carry
   editorial insertions like *"the girl playing trombone … that came in here with
   Redd Foxx? [Melba Liston]-ed"*, and Smithsonian ones expand a bare first name
   as *"Melba [Liston]"*. The block is still about her (`is_about_subject:
   true`), but note that the name is editorial — and a `pull_quote` containing
   the bracketed insertion is fine only if it is an exact substring.
4. **Interviewer prompts answered with "Yeah."** Several Rutgers blocks are the
   interviewer (often Patricia Willard) asking *"you remember Melba Liston and
   that gang"* and getting assent. That is `interviewer_question`; summarize the
   **answer** found in `context_after` and say in `notes` whether the interviewee
   added anything of their own.
5. **Page-break splits invert meaning.** When `target_ends_midsentence` or
   `target_starts_midsentence` is true, the adjacent block is **mandatory**
   reading.
6. **Pronouns flip inside a block.** "She" after a Liston mention can become
   Mary Lou Williams, Vi Redd, Billie Holiday, Patti Bown or the interviewee's
   wife within a sentence. Check antecedents inside the target, not just before.
7. **Lists.** She is very often one name in a section roll-call (*"Åke Persson
   playing lead, Melba Liston, Curtis Fuller, and myself"*). That is `list_item`
   unless the speaker goes on to say something about her.
8. **Speaker mis-segmentation.** `speaker_role` is a heuristic and is sometimes
   wrong — trust the text over the label. Rutgers transcripts label the
   questioner `Q`/`I:` and leave answers unlabelled.
9. **Titles containing her name**: *Melba Liston and Her 'Bones* (1959),
   *Melba and her 'Bones*. A block whose only mention is the record title is
   about the record — usually `passing_reference`, `notable: 0–1` — not a false
   positive.
10. **Archive apparatus is ingested as speech**: front-matter biographies,
    transcriber's notes, rights statements, back-matter indexes (*"Liston,
    Melba, 87"* in the Shirley Horn transcript). `archive_boilerplate`,
    `notable: 0`.

## Your output

Write `liston/eval_output/chunk_NNN.json`:

```json
{"subject": "liston", "chunk": N, "count": <n>,
 "chunk_top": [<block_id>, <block_id>, <block_id>],
 "items": [ ... ]}
```

One record per input item, **in the same order, one per input item, no drops**:

```json
{
 "block_id": 272159,
 "is_about_subject": true,
 "mention_kind": "substantive_comment",
 "quotes_the_subject": false,
 "stance": "positive",
 "stance_strength": 2,
 "stance_target": "subject",
 "content_type": ["personal_memory", "musical_assessment"],
 "relationship": "personally",
 "block_is_firsthand": true,
 "topics": ["Dizzy Gillespie big band", "arranging"],
 "summary": "Hampton recalled that Liston was musical director and main arranger of the band he joined.",
 "pull_quote": "Melba Liston was the musical director",
 "notable": 2,
 "context_changed_reading": true,
 "truncated_target": false,
 "confidence": "high",
 "notes": ""
}
```

### Field definitions

**`is_about_subject`** (bool) — does this block actually concern Melba Liston?
False for the trap cases above. If false, set `mention_kind: "false_positive"`,
`stance: null`, `stance_strength: 0`, `content_type: []`, `summary: ""`,
`pull_quote: null`, `notable: 0`, and explain in `notes` who it is really about.

**`mention_kind`** — exactly one of:
- `substantive_comment` — the speaker says something of substance about her
- `quoted_speech` — the block reports words **Liston herself said** (prefer this
  over `substantive_comment` when the block's value is her own words)
- `passing_reference` — named in passing, no real content
- `list_item` — one name in a list of names
- `interviewer_question` — the *interviewer* raises her; the answer is usually
  in `context_after` — summarize the **answer** and say so in `notes`
- `third_party_topic` — the block is about two *other* people, she is incidental
- `archive_boilerplate` — not interview speech at all (headers, front matter,
  indexes, rights statements, transcriber's notes outside a turn)
- `false_positive` — not actually about her
- *(own interview only)* `peer_interviewer_testimony` — Clora Bryant states
  something substantive about Liston, to Liston
- *(own interview only)* `self_account` — Liston is the speaker
- *(own interview only)* `transcriber_summary` — the mention is only inside a
  transcriber's square-bracketed summary

**`quotes_the_subject`** (bool) — does the block contain reported speech by
Liston? Can be true alongside any `mention_kind`. Always false when she is
herself the speaker.

**`stance`** — `positive` | `negative` | `mixed` | `neutral` | `null`.
Neutral = factual/biographical, no evaluative content. Do not inflate:
admiration is common in this corpus, but so is frank criticism and praise that
carries a reservation, and "mixed" is the honest answer more often than people
expect. Judge the *speaker's* attitude, not her reputation.

For `interviewer_question` items, score the **interviewer's own framing** if it
carries an attitude, else neutral. Such items may never exceed `notable: 1`.

**`stance_target`** — `subject` | `women_in_jazz` | `associates`.
Stance is always scored toward *Liston herself*. A recurring pattern in this
material is that she is cited as the exception that proves a rule about women
musicians (*"It's a rare woman, like Melba Liston, who comes to the music for the
music"*). When the evaluative content is really a generalisation about women
players, set `stance_target: "women_in_jazz"` and score `stance` on what is said
about her specifically. Use `associates` when the judgement lands on the band or
leader she was with.

**`stance_strength`** 0–3 — 0 none, 1 mild, 2 clear, 3 emphatic.

**`content_type`** — one or more of: `personal_memory`, `anecdote`,
`musical_assessment`, `influence`, `legacy_influence`, `mentorship`,
`biographical_fact`, `hearsay`, `comparison`, `character_description`,
`working_relationship`, `arranging_composing` (her writing, as opposed to her
playing), `gender` (the block turns on her being a woman in a male profession),
`humor`, `criticism`, `historical_context`, `health` (the stroke and after).

**`relationship`** — the speaker's relation to her, judged from the whole window
and **kept consistent across every item from the same interview**:
`personally` (played with / met / knew her), `secondhand` (knows of her, heard
stories), `unclear`, `not_applicable` (a neutral interviewer, Liston herself, or
a false positive). If any block in the window shows first-person contact, use
`personally` throughout that document. Do not use outside biographical knowledge.

**`block_is_firsthand`** (bool) — does *this specific block* report the speaker's
own direct experience of her (vs. general opinion or hearsay)?

**`topics`** — 0–4 short free-text tags (bands, venues, records, concepts).

**`summary`** — ONE sentence, past tense, naming the speaker by surname: what
they say about her. For `interviewer_question`, summarize the answer. Empty
string for false positives and boilerplate.

**`pull_quote`** — the best display sentence(s) for a web page. It **MUST be an
exact, contiguous substring of `target.text`** — no ellipsis, no reordering, no
case changes, no splicing across blocks. Trim to a sentence boundary; if no clean
boundary exists, quote the fragment and note it. `null` if nothing is quotable.
This is validated programmatically; a non-substring is a hard failure.

**`notable`** 0–3 — how good is this for the page?
- `3` = a sentence you would set in 24pt type under a photograph: vivid,
  specific, about her, needs no setup. **Hard quota: at most 5 items per chunk.**
- `2` = solid, usable with a little context
- `1` = minor
- `0` = unusable
Be a harsh grader. Most items are 0–1.

**`chunk_top`** (top-level) — the `block_id`s of the 3 best items in your chunk,
best first.

**`context_changed_reading`** (bool) — true if the expanded context changed how
you read the target block versus reading it alone. Be honest.

**`truncated_target`** (bool) — the target block begins or ends mid-sentence at a
page break. (The input pre-flags this; correct it if the flag is wrong.)

**`confidence`** — `high` | `medium` | `low` for your own judgement.

**`notes`** — short free text, or `""`. Ambiguous pronouns, speaker
mis-segmentation, an editorially inserted name, suspected metadata errors, a
conflict with another item — anything a human should check.

## Write incrementally — this is mandatory

1. **Before you start**, check whether your output file already exists. If it
   does, read it, count the valid records, and resume from the next item.
2. **Write after every 15 items.** Rewrite the whole output file each time with
   everything finished so far (`count` = records actually written).
3. Only the final write needs to satisfy the full-count validation.

## Rules

- **Never invent text.** Every `pull_quote` must appear verbatim in `target.text`.
- **Don't use outside knowledge** to decide what someone said — only the window.
  Outside knowledge is fine for recognizing a name or a record title.
- Do not fix, clean, or improve transcript text. Quote around ASR/OCR errors or
  leave the item unquotable.
- If a window is garbled, say so in `notes` and lower `confidence`.
- Output valid JSON, UTF-8, `ensure_ascii=False`. Write it with a short Python
  script run via `uv run --python 3.14 python <script>` — do not print records to
  the terminal.
- **Other agents run concurrently.** Any helper script you write MUST live in
  the scratchpad directory you were given and carry your chunk number in its
  filename. Write to no path in the project other than your own output chunk.
  Do not run git commands.
- Exactly as many output records as input items, in the same order.
- **Validate before finishing** (short Python script): output parses, record
  count equals input count, `block_id` at each index matches the input, every
  non-null `pull_quote` is an exact substring of that item's `target.text`, no
  `pull_quote` contains text from inside a transcriber's square brackets in an
  own-interview chunk, and no more than 5 items have `notable == 3`.
