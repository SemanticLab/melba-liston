# Her-words spec — what Melba Liston said about the people in her life

Project root: `/Users/m/git/liston-centennial-2026`

Melba Liston (trombonist, arranger, composer; 1926–1999) gave one oral-history
interview that survives in this corpus: the Smithsonian Jazz Oral History
Program, 4–5 December 1996, at her home in Los Angeles. You are reading it to
establish, for each person named in it, **what she actually said about them and
how she knew them** — for a centennial web page.

## Read this before anything else

1. **The interviewer is a peer.** Speaker `Bryant` is **Clora Bryant**
   (1927–2019), a trumpeter and a decades-long friend. She knows Liston's life
   and often *tells* it: long, fact-laden turns that Liston answers with
   "Yeah."
2. **Liston had a stroke in 1985.** She has memory loss and difficulty
   speaking. Her turns are short. Many are a bare "Yeah." or "No."
3. **Square brackets are the transcriber, not a speaker.** Where Liston could
   not answer or could not be understood, the transcriber substituted a summary:
   *"[Liston cannot recall what happened next.]"*, *"[names other bandmembers:
   John Collins, Jimmie Heath, …]"*. Bracketed text is evidence about the
   interview; it is **never her words** and must never be quoted as hers. Short
   bracketed insertions inside a real sentence — *"Charli [Persip]"* — are
   editorial name expansions.

The upstream model that first classified these relationships did not respect any
of this. It routinely took what Bryant said for what Liston said, and it typed
tune titles ("Little Niles", "Anitra") and descriptors ("Saxophone player") as
people. Your job is to replace its output with a reading a human would trust.

## Your input

- **`liston/own_interview.txt`** — the whole transcript, one block per line:

  ```
  [b295466 p0.10] Liston: I was born in Kansas City, Missouri, …
  ```

  `b295466` is the `block_id`; `p0.10` is page.block; a `*` after the speaker
  (`Liston*`) means the label was inherited across a page break. **Read the
  entire file first, start to finish.** It is about 125,000 characters. People
  recur; the interview circles back; an answer on page 40 can settle a question
  from page 9.
- **`liston/her_words_input/chunk_NNN.json`** — your ~30 people. Each item:

  ```
  person_id               the key — copy it through
  as_named_in_interview   the name string as the transcript has it
  surface_forms           every variant folded into this person
  upstream_identity       the Wikidata match the pipeline made (qid may be null)
  n_mentions, mention_block_ids   where the name appears (block_ids, no "b" prefix)
  is_interviewer          true for Clora Bryant herself
  upstream                the earlier model's relation, direction, evidence —
                          a lead to check, NOT a finding
  ```

`mention_block_ids` lists only the blocks where the *name* was detected. The
person may also be discussed by pronoun in the blocks around them — that is why
you read the whole transcript.

## Your output

Write `liston/her_words_output/chunk_NNN.json`:

```json
{"subject": "liston", "chunk": N, "count": <n>,
 "chunk_top": [<person_id>, <person_id>, <person_id>],
 "items": [ ... ]}
```

One record per input item, **same order, no drops**. (The values below show the
shape only — the person and the quotes are invented.)

```json
{
 "person_id": 100001,
 "is_person": true,
 "not_person_kind": null,
 "name": "Jane Example",
 "identity_ok": true,
 "identity_note": "",
 "who_speaks_of_them": "both",
 "basis": "her_statement",
 "relation": "collaborated with",
 "direction": "mutual",
 "tie": ["arranging_client"],
 "firsthand": true,
 "stance": "positive",
 "stance_strength": 2,
 "era": "late 1950s",
 "summary": "Liston said she wrote a set of arrangements for Example and enjoyed the work.",
 "one_liner": "wrote arrangements for her album",
 "her_quote": "I wrote those for her. I liked doing that.",
 "her_quote_block_id": 290001,
 "bryant_quote": null,
 "bryant_quote_block_id": null,
 "more_her_quotes": [{"block_id": 290010, "quote": "She could really sing."}],
 "topics": ["strings", "ballads"],
 "notable": 2,
 "upstream_relation_ok": true,
 "confidence": "high",
 "notes": ""
}
```

### Field definitions

**`is_person`** (bool) — is this entry a real, individual human being?
False for tune titles (*Little Niles*, *Anitra's Dance*, *Pam's Waltz*), group or
company names, and descriptors ("Saxophone player", "Horn players", "NEA Jazz
Master"). If false: set `not_person_kind` to `tune_title` | `group_name` |
`company` | `descriptor` | `place` | `other`, set `relation: "none"`, `basis:
"none"`, `notable: 0`, all quotes null, `summary: ""`, `one_liner: ""`, and say
what it really is in `notes`. A tune *named after* a real person (Randy Weston's
son Niles) is still `tune_title` if the transcript is discussing the tune.

**`name`** — the best full name for the person **as the transcript supports it**.
Expand "Diz" to "Dizzy Gillespie" when the interview makes that plain; leave a
bare "Lorenzo" bare if it never says more.

**`identity_ok`** (bool) / **`identity_note`** — is `upstream_identity` (the
Wikidata match) the right person, judging from the transcript? `true` when it is
plainly right, or when there is no upstream QID and nothing to dispute. `false`
when the match is wrong or when two different people were folded together — say
which in `identity_note`. If you are confident of the correct person and they are
well known, name them there; **do not invent a QID**.

**`who_speaks_of_them`** — `liston` | `bryant_only` | `both` |
`transcriber_only`. Who actually utters anything about this person?
`transcriber_only` = they appear only inside a bracketed summary.

**`basis`** — what the relationship finding rests on. Exactly one:
- `her_statement` — Liston says it herself, in her own words
- `her_assent` — Bryant states it and Liston confirms ("Yeah.", "Um-hmm.",
  or adds a small detail). The fact is established, but the words are Bryant's.
- `bryant_only` — Bryant says it; Liston does not confirm, contradicts it, or
  talks about something else
- `transcriber_summary` — only a bracketed summary supports it
- `none` — nothing in the transcript establishes a relationship

**`relation`** — Liston's relation to this person. One term from the corpus's
controlled vocabulary, or `none`:

| term | use when |
|---|---|
| `in music group with` | they were members of the same working band |
| `collaborated with` | made music together outside a shared standing band: she arranged or composed for them, recorded with them, co-wrote |
| `played with` | performed together, no more than that is said |
| `toured with` | specifically travelled on a tour together |
| `played under` | one was the leader the other worked for |
| `mentor of` | one taught, trained or guided the other |
| `influenced by` | one's music shaped the other's, with or without contact |
| `friend of` | a personal friendship is stated |
| `acquaintance of` | they knew each other; no more is established |
| `has met` | a meeting or encounter, nothing ongoing |
| `knows of` | she knew of them (heard them, admired them, was asked about them) with no contact established |
| `none` | no relation between Liston and this person is established — e.g. Bryant mentions them and Liston says nothing |

Pick the **strongest relation the transcript actually supports**, and be
conservative: a name in a transcriber's roll-call of band members supports
`in music group with` only with `basis: "transcriber_summary"`. Family members
take `none` here and are described by `tie` — the vocabulary has no kinship term.

**`direction`** — for the asymmetric relations (`played under`, `mentor of`,
`influenced by`), who holds the senior role. Exactly one of:
- `other_leads` — the other person is the leader / teacher / influence
  (she played in Dizzy Gillespie's band → `played under`, `other_leads`)
- `liston_leads` — Liston is the leader / teacher / influence
  (a trombonist who played in her band → `played under`, `liston_leads`)
- `mutual` — the relation is symmetric (`in music group with`, `collaborated
  with`, `played with`, `toured with`, `friend of`, `acquaintance of`, `has met`)
- `na` — the relation is `knows of` or `none`

**`tie`** — one or more of: `bandmate`, `bandleader` (they led a band she was
in), `sideman` (they played in a band she led), `arranging_client` (she wrote
for them), `fellow_arranger`, `teacher`, `student`, `family`, `school_friend`,
`romantic`, `friend`, `employer_nonmusic`, `admired`, `heard_on_radio_or_record`,
`younger_generation`, `interviewer`, `recording_staff`, `unknown`.

**`firsthand`** (bool) — does the transcript show Liston's own direct contact
with this person?

**`stance`** — `positive` | `negative` | `mixed` | `neutral` | `null` — Liston's
attitude toward them, from what **she** says. `null` when she expresses none.
**`stance_strength`** 0–3.

**`era`** — when the connection was, as the transcript gives it ("1943–44",
"late 1950s", "childhood"), or `""`.

**`summary`** — ONE sentence, past tense, naming her as "Liston": what she said
about this person, or what was established about them. If the content is
Bryant's with Liston assenting, say so ("Bryant recalled …; Liston agreed").
Empty string only when `is_person` is false.

**`one_liner`** — a phrase of **at most eight words**, lower case, no full stop,
that completes "Melba Liston …" or stands alone as a caption for how she knew
them: *"wrote the arrangements for her 1959 album"*, *"taught her to stage a
skit"*, *"was at school with him"*. Every place, person, title and year in it
must be in the transcript. Empty string if nothing is established.

**`her_quote`** / **`her_quote_block_id`** — the best sentence(s) **Liston
herself** says about this person. It MUST be an exact, contiguous substring of
the text of ONE block whose speaker is `Liston` (or `Liston*`), and it must not
include any transcriber's bracketed summary. A bare "Yeah." is not a quote.
`null` if she never says anything quotable about them. `her_quote_block_id` is
the integer block id (no "b").

**`bryant_quote`** / **`bryant_quote_block_id`** — when `basis` is `her_assent`
or `bryant_only`, the sentence(s) of **Bryant's** that carry the content: an
exact, contiguous substring of ONE `Bryant` block. `null` otherwise, or when
Liston's own quote says it all.

**`more_her_quotes`** — up to 4 further quotable Liston lines about the same
person, each `{block_id, quote}` under the same exact-substring rule. `[]` if
none.

**`topics`** — 0–4 short free-text tags (bands, records, tunes, places).

**`notable`** 0–3 — how good is this person's entry for the page?
- `3` = she says something about them you would print large: vivid, specific,
  in her own words. **Hard quota: at most 5 per chunk.**
- `2` = a real relationship with a usable quote
- `1` = established but thin (assent only, a roll-call name)
- `0` = nothing usable, or not a person

**`upstream_relation_ok`** (bool) — was the earlier model's `upstream.relation`
right? (Measurement only; be honest.)

**`confidence`** — `high` | `medium` | `low`. **`notes`** — anything a human
should check: a callback to another page, a contradiction between two passages,
garbled text, a suspected transcription error in a name.

**`chunk_top`** (top-level) — the 3 best `person_id`s in your chunk, best first.

## Write incrementally — mandatory

1. Before you start, check whether your output file exists; if so, resume after
   the last valid record.
2. Rewrite the whole output file after every 10 people (`count` = records
   written so far).

## Rules

- **Never invent text.** Quotes are exact substrings of a single block.
- **Only the transcript decides what she said.** Outside knowledge may be used
  to recognise who a name refers to and to spell it — never to supply a fact
  about her relationship with them that the transcript does not contain.
- Do not fix or tidy transcript text inside a quote.
- Output valid JSON, UTF-8, `ensure_ascii=False`. Write it with a short Python
  script run via `uv run --python 3.14 python <script>`.
- **Other agents run concurrently.** Helper scripts go in the scratchpad
  directory you were given, with your chunk number in the filename. Write to no
  path inside the project except your own output chunk. Do not run git commands.
- **Validate before finishing** against `liston/own_interview.json` (its
  `items[]` carry `block_id`, `speaker_effective`, `speaker_role` and `text`):
  output parses; record count and `person_id` order match the input; every
  `her_quote` / `more_her_quotes[].quote` is an exact substring of the `text` of
  the named block **and that block's `speaker_role` is `subject`**; every
  `bryant_quote` is an exact substring of a block whose `speaker_role` is
  `interviewer`; no Liston quote overlaps a `[...]` span longer than 25
  characters; `direction` is one of the four allowed values; at most 5 items
  have `notable == 3`.
