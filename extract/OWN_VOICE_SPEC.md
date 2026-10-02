# Own-voice spec — Melba Liston in her own words

Project root: `/Users/m/git/liston-centennial-2026`

Melba Liston (trombonist, arranger, composer; 1926–1999) gave one oral-history
interview that survives in this corpus: the Smithsonian Jazz Oral History
Program, 4–5 December 1996, at her home in Los Angeles. A centennial web page
will be built from it. The two centennial subjects done before her — John
Coltrane and Miles Davis — were never interviewed, so their pages could only
show what other people said. Hers can show **her**.

## Read this before anything else

1. **The interviewer is a peer.** Speaker `Bryant` is **Clora Bryant**
   (1927–2019), a trumpeter and a decades-long friend. She knows Liston's life
   and often *tells* it; Liston answers "Yeah."
2. **Liston had a stroke in 1985.** She has memory loss and difficulty speaking.
   Her turns are short. When she does say a full sentence it tends to be plain
   and exact, and that plainness is the voice — do not pass over a line because
   it is short.
3. **Square brackets are the transcriber, not a speaker.** Where Liston could
   not answer or could not be understood the transcriber substituted a summary:
   *"[Liston cannot recall what happened next.]"*. Bracketed text is **never her
   words** and must never be quoted as hers. Short bracketed insertions inside a
   real sentence — *"Charli [Persip]"* — are editorial name expansions; avoid
   them in quotes where you can.

## Your input

- **`liston/own_interview.txt`** — the whole transcript, one block per line:

  ```
  [b295466 p0.10] Liston: I was born in Kansas City, Missouri, …
  ```

  `b295466` is the `block_id`; `p0.10` is page.block; `*` after a speaker means
  the label was inherited across a page break. **Read the entire file, start to
  finish, before writing anything.** About 125,000 characters.
- **`liston/own_interview.json`** — the same blocks as structured data
  (`items[]`: `block_id`, `speaker_effective`, `speaker_role` = `subject` |
  `interviewer` | `none`, `text`, `people[]`). Use it for validation.
- **`liston/her_relationships.json`** — the people the pipeline detected in the
  interview (`items[].person.as_named_in_interview`, plus `skipped.items`). You
  need it only for Part C.

(All block ids and values in the examples below are invented, to show shape only.)

Your assignment says which **parts** to produce. Each part is its own output
file. Do only the parts you are assigned.

---

## Part A — `liston/own_voice_output/self.json`: Liston on herself

Her best lines about **her own life and work**. Not what she says about other
people for their own sake (another pass does that) — what she says about being
Melba Liston: the horn, the writing, the road, being the only woman on the
bandstand, quitting, coming back, the stroke, the computer.

```json
{"subject": "liston", "part": "self", "count": <n>,
 "top": [<block_id>, <block_id>, <block_id>, <block_id>, <block_id>],
 "items": [
  {"block_id": 290001,
   "pull_quote": "exact contiguous substring of that Liston block",
   "theme": ["origins"],
   "period": "childhood",
   "summary": "One sentence, past tense: what she is saying and about what.",
   "prompted_by": "what Bryant had just asked or said, in a few words",
   "stands_alone": true,
   "context_block_ids": [290000],
   "stance": "neutral",
   "notable": 2,
   "notes": ""}
 ]}
```

- Select **every** Liston line worth showing — expect somewhere between 50 and
  120. Completeness matters more than a tidy number: a later step filters by
  `notable`. One item per block; if a block holds two separable quotes, pick the
  better and mention the other in `notes`.
- **`pull_quote`** — exact, contiguous substring of ONE block whose
  `speaker_role` is `subject`. No ellipsis, no splicing, no tidying. Must not
  include a transcriber's bracketed summary.
- **`theme`** — one or more of this closed list:
  `origins` (birth, family, Kansas City, the move to Los Angeles) ·
  `learning` (first trombone, teachers, school, Alma Hightower) ·
  `first_work` (Lincoln Theater pit band, Bardu Ali, early jobs) ·
  `big_bands` (Gerald Wilson, Gillespie, Basie, Quincy Jones — life in the sections) ·
  `the_road` (touring, the South, Billie Holiday tour, buses, hotels) ·
  `being_a_woman` (the only woman in the band; how men treated her; other women players) ·
  `race` (segregation, Jim Crow, "whitey") ·
  `arranging` (how she writes; voicings; strings; writing for singers) ·
  `composing` (her own tunes) ·
  `the_trombone` (playing, sound, her feelings about the instrument) ·
  `own_bands` (Melba Liston and Her 'Bones, her all-women group, Melba Liston & Company) ·
  `randy_weston` (the partnership) ·
  `studio_work` (Motown, record dates, commercial writing) ·
  `leaving_music` (the Board of Education years; quitting) ·
  `jamaica` (teaching there in the 1970s) ·
  `teaching` (students, young players, advice) ·
  `stroke` (illness, recovery, writing by computer) ·
  `money_and_credit` (pay, royalties, recognition, being overlooked) ·
  `music_today` (her opinions on current music) ·
  `character` (a line that simply shows who she is: humour, bluntness, modesty)
- **`period`** — when the thing she describes happened, as the transcript gives
  it, or `""`.
- **`stands_alone`** (bool) — can the quote be read cold, with no setup?
  If false, `context_block_ids` must list the block(s) a reader needs (usually
  Bryant's question immediately before).
- **`stance`** — her attitude to what she is describing: `positive` | `negative`
  | `mixed` | `neutral`.
- **`notable`** 0–3 — `3` = set it in large type under her photograph. **At most
  12 items may be 3.** `2` = good, usable. `1` = minor but real. Do not include
  `0`s.
- **`top`** — your five best, best first.

Also include, at the top level of this file:

```json
"timeline": [
  {"when": "1926", "sort_year": 1926, "event": "Born in Kansas City, Missouri.",
   "block_ids": [290001], "stated_by": "liston", "confirmed_by_liston": true, "notes": ""}
]
```

Every datable or sequenceable biographical fact **the transcript itself states**
— births, moves, schools, bands joined and left, tours, records, jobs, the
stroke, awards. `stated_by`: `liston` | `bryant` | `transcriber`.
`confirmed_by_liston`: true when she says it or clearly assents. `sort_year` is
your best integer year for ordering, or `null` when the transcript gives no way
to place it. Do not add facts from outside knowledge; if the transcript's date
conflicts with what you know, record the transcript's version and say so in
`notes`.

---

## Part B — `liston/own_voice_output/bryant.json`: Clora Bryant on Liston

Everything of substance **Bryant says about Liston** — to her face, in the
second person. Praise, musical judgement, shared memories, facts about Liston's
life that Bryant supplies. Whether or not the block contains the name "Melba".
Exclude plain questions and housekeeping.

```json
{"subject": "liston", "part": "bryant", "count": <n>,
 "top": [<block_id>, <block_id>, <block_id>],
 "items": [
  {"block_id": 290002,
   "pull_quote": "exact contiguous substring of that Bryant block",
   "kind": "musical_assessment",
   "summary": "One sentence, past tense, naming Bryant.",
   "about": "one of her arrangements",
   "liston_response": "deflects",
   "liston_response_block_id": 290003,
   "stance": "positive",
   "stance_strength": 2,
   "notable": 2,
   "notes": ""}
 ]}
```

- **`pull_quote`** — exact, contiguous substring of ONE block whose
  `speaker_role` is `interviewer`; no bracketed transcriber text.
- **`kind`** — `praise` | `musical_assessment` | `shared_memory` |
  `biographical_fact` (Bryant supplies a fact of Liston's life) |
  `character_description` | `tribute` (a statement of what Liston meant to her
  or to others).
- **`about`** — what the remark concerns, in a few words.
- **`liston_response`** — `confirms` | `elaborates` | `deflects` | `denies` |
  `no_response`, and the block id of her reply (`null` if none).
- **`notable`** 0–3, **at most 8 items may be 3**; do not include `0`s.
- Expect 30–80 items.

---

## Part C — `liston/own_voice_output/missed_people.json`: people the pipeline missed

The automatic name detection missed people — especially names that appear only
inside the transcriber's brackets, or that Liston says in a clipped way. List
**every real person named or clearly identified in the transcript who is NOT
already in `liston/her_relationships.json`** (compare against
`items[].person.as_named_in_interview`, `items[].person.surface_forms` and
`skipped.items[]`; match loosely — "Diz" is already there as "Dizzy
[Gillespie]").

```json
{"subject": "liston", "part": "missed_people", "count": <n>,
 "items": [
  {"name": "John Example",
   "as_in_transcript": ["Mr. Example"],
   "block_ids": [290004, 290009],
   "who_is_this": "a music teacher at her school",
   "who_speaks_of_them": "both",
   "basis": "her_statement",
   "relation": "mentor of",
   "direction": "other_leads",
   "tie": ["teacher"],
   "firsthand": true,
   "summary": "One sentence, past tense.",
   "one_liner": "at most eight words, lower case",
   "her_quote": "exact substring of ONE Liston block, or null",
   "her_quote_block_id": 290005,
   "bryant_quote": null,
   "bryant_quote_block_id": null,
   "notable": 2,
   "confidence": "high",
   "notes": ""}
 ]}
```

The fields mean exactly what they mean in `extract/HER_WORDS_SPEC.md` — **read
its "Field definitions" section** for the vocabularies of `who_speaks_of_them`,
`basis`, `relation`, `direction`, `tie`. `who_is_this` is a plain description
from the transcript. If there are no missed people, write an empty `items` list;
do not pad.

---

## Rules for all parts

- **Never invent text.** Every quote is an exact, contiguous substring of ONE
  block's `text` in `own_interview.json`, spoken by the right voice.
- **Only the transcript decides what was said.** Outside knowledge may be used
  to recognise and spell a name or a title — never to supply a fact.
- Do not fix or tidy transcript text inside a quote.
- Output valid JSON, UTF-8, `ensure_ascii=False`, written by a short Python
  script run via `uv run --python 3.14 python <script>`.
- **Write incrementally**: check whether your output file already exists and
  resume; rewrite the file after every ~20 items.
- **Other agents run concurrently.** Helper scripts go in the scratchpad
  directory you were given, with your part name in the filename. Write to no
  path inside the project except your own output file(s) under
  `liston/own_voice_output/`. Do not run git commands.
- **Validate before finishing**: output parses; every quote is an exact
  substring of the named block; Liston quotes come from `speaker_role ==
  "subject"` blocks and Bryant quotes from `speaker_role == "interviewer"`
  blocks; no quote overlaps a `[...]` span longer than 25 characters; the
  `notable == 3` quotas hold; every `block_id` you cite exists.
