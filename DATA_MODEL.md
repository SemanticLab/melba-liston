#   Data model — what's here, and how it joins

A UI-oriented inventory for the Melba Liston centennial data. Counts are read
from the files. Everything is static JSON; there is no server and no database at
runtime. The largest file is 861 KB (`liston/people.json`), so nothing here needs
sharding the way the Coltrane / Davis bundle did.

Read `README.md` first for what the passes did and what to be careful of.

---

## 1. Three directions, one person index

The Coltrane / Davis data had one direction: people talking about the subject.
This has three, because Liston was interviewed herself.

| Direction | File | Unit | Count |
|---|---|---|---:|
| others → her | `witnesses.json` | one row per interview | 25 (21 real) |
| | `enriched.json` / `best_quotes.json` | one row per block | 118 / 21 |
| her → others | `her_words.json` | one row per person | 122 (106 real) |
| her → herself | `own_voice.json` → `self` | one row per line | 173 |
| Bryant → her | `own_voice.json` → `bryant` | one row per line | 83 |

`people.json` (487) folds all of it — plus the discography roster and the network
— into **one record per person** with a boolean per layer. Start a page from
`people.json` and follow it out to the layer files for detail.

## 2. Keys

| Entity | Key | Example | Authoritative in |
|---|---|---|---|
| Person | `qid` | `Q1371187` | `people.json`, `shared/images.json` |
| Document (an interview) | `doc_id` | `Hampton_Slide_Transcript`, `275930` | `documents.json` |
| Block (a passage) | `block_id` (int) | `275470` | `enriched.json`, `own_interview.json` |
| Release | `qid` (+ `title`) | `Q55622715` | `discography.json` |
| Person within her interview | `person_id` (int) | `104375` | `her_words.json` |

A person has no QID in three situations, and then has no portrait, Wikipedia link
or cross-layer join: 34 `nm:` + 17 `loc:` network nodes, 166 name-only roster
credits, and 38 of the 106 people in her interview (family, schoolmates,
teachers). `people.json` keys those `name:<normalised name>`.

`her_own_interview = "Liston_Melba_Interview_Transcription"`. Any block-level file
may contain blocks from it; they carry `own_interview: true`.

Deep links are already formed on every record:
`<transcript_url>#b<page>-<block>` opens the transcript reader at the block.

## 3. The join graph

```
                         shared/images.json  (459 people, by qid)
                                   │ qid
                                   ▼
        ┌──────────────────── people.json (487) ─────────────────────┐
        │ witness           │ she_spoke_of      │ on_her_records     │ network
        ▼                   ▼                   ▼                    ▼
  witnesses.json      her_words.json   discography_personnel   connections.json
   (25 rows)           (122 rows)          (582 people)          (123 edges)
        │ block_ids         │ *_block_id        │ albums[]
        ▼                   ▼                   ▼
  enriched.json       own_interview.json   discography.json
  (118 blocks)         (1,057 blocks)       (80 releases)
        │                   ▲
        ▼                   │ block_id
  best_quotes.json     own_voice.json
     (21)             self 173 · bryant 83 · timeline 53
```

Verified by `extract/verify_all.py`: `best_quotes ⊆ enriched = quotes`; every
`doc_id` in `enriched.json` is in `documents.json` (`items` or
`text_hit_only_documents`); every quote in every file resolves to its block in
the source database.

Joins that are already materialised, so a page need not make them:

- `witnesses.json` rows carry `she_said` (what *she* said about that witness),
  `albums_with_her`, and `image`.
- `discography_personnel.json` people carry `quotes[]` (what they said about her)
  and `she_said`.
- `people.json` carries all four layers side by side.

## 4. The files a page should read

### `liston/people.json` — everyone, once

`key`, `qid`, `name`, `description`, `born`, `died`, `image`, `notable`, and

| field | when true, detail is in |
|---|---|
| `witness` | `witness_rows[]` — relation, tier, one_liner, lead_quote, caution, doc |
| `she_spoke_of` | `she_said` — relation, basis, tie, one_liner, her_quote, bryant_quote |
| `on_her_records` | `records` — album_count, albums[], instruments[] |
| `network` | `edge` — weight, relations[], community_label, evidence_url |

`layers[]` lists the true ones; `both_directions` = witness **and** she_spoke_of
(8 people). Sorted: both directions first, then `notable`, then number of layers.
Layer counts: witness 20 · she_spoke_of 90 · on_her_records 418 · network 72.
414 people are in exactly one layer; 5 are in all four.

### `liston/witnesses.json` — others → her

One row per interview. The fields that drive a card:

- `name`, `qid`, `description`, `image`
- `relation` (11-term vocabulary + `none`), `relation_weight`, `tier`
  (`band` / `learned` / `social` / `knew_of` — the same four tiers as the
  Coltrane / Davis page), `direction`, `contact_level`, `basis[]`, `context`
- `one_liner` — the caption phrase, 3–8 words; `grounded` says whether every
  content word is in the testimony (18 of 21 are; the three misses are
  paraphrase, listed in `ungrounded_words`)
- `lead_quote` + `lead_url`, `second_quote`, `more_quotes[]`
- `stance`, `notable` 0–3
- **`caution`** — non-empty on every row. Read it before showing the quote.
- `spoke_themselves` — `false` on 4 rows: filter them out of any "witness" list.
- `doc` — the interview, with `transcript_url` and `source_url`

Slide Hampton has two rows (two interviews, two archives); `people.json` folds
them.

### `liston/her_words.json` — her → others

One record per person named in her interview.

- `is_person` — `false` for 16 entries (tune titles, a playground, descriptors);
  `not_person_kind` says what. Filter these out.
- `basis` — **the field to filter on**: `her_statement` (53) · `her_assent` (16)
  · `transcriber_summary` (14) · `bryant_only` (7) · `none` (16)
- `relation`, `direction` (`other_leads` / `liston_leads` / `mutual` / `na`),
  `tie[]` (bandmate, arranging_client, teacher, family, school_friend, romantic…),
  `era`
- `her_quote` + `her_quote_url` — her own words, verified; `more_her_quotes[]`
- `bryant_quote` — when the content was Bryant's and Liston assented
- `one_liner`, `summary`, `stance`, `notable`
- `qid`, `identity_ok`, `identity_note`, `fold_contaminated`
- `source` — `person_layer` or `reader_added` (9 people the name detection
  missed, including Quincy Jones and Abbey Lincoln)
- `upstream` — the earlier model's answer and whether it was right

Top-level `merged` holds the 5 absorbed duplicate records; `unmerged_leads` holds
4 identity problems left for a human.

### `liston/own_voice.json` — her → herself, Bryant → her, the timeline

- `self.items[]`: `pull_quote`, `theme[]` (20 closed values — see `themes`),
  `period`, `summary`, `prompted_by`, `stands_alone`, `notable` 1–3, `exchange`
  (the turns around it, so the question can be shown above the answer), `url`.
  Themes by count: character 49 · arranging 41 · stroke 26 · being_a_woman 21 ·
  big_bands 19 · learning 18 · the_trombone 17 · teaching 14 · randy_weston 11…
- `bryant.items[]`: `pull_quote`, `kind` (biographical_fact 25 ·
  musical_assessment 21 · tribute 16 · praise 8 · shared_memory 8 ·
  character_description 5), `about`, `liston_response` (elaborates 32 · confirms
  17 · deflects 16 · denies 10 · no_response 8) with `liston_response_text`.
- `timeline.items[]`: `when`, `sort_year` (null on 22 undatable entries — keep
  `order`), `event`, `stated_by` (liston 30 · bryant 18 · transcriber 5),
  `confirmed_by_liston`, `block_ids`, `url`.

### `liston/enriched.json` and `best_quotes.json` — the block level

Same shape as the Coltrane / Davis files, with two extra fields
(`own_interview`, `mention_source`) and three extra `mention_kind` values used
only inside her own interview: `peer_interviewer_testimony` (Bryant, 16),
`self_account` (Liston speaking, 9), `transcriber_summary` (12). Context windows
are embedded (`context_before` / `context_after`).

`best_quotes.json` = about her, `notable ≥ 2`, verbatim quote, and `mention_kind`
in {substantive_comment, quoted_speech, peer_interviewer_testimony}. `self_account`
is deliberately excluded — her own voice is `own_voice.json`'s job.

### `liston/discography.json` and `discography_personnel.json`

Per release: the usual infobox fields, `tracks[]`, `personnel[]`, plus

- `subject_role` — `sidewoman` 49 · `arranger` 16 · `composer` 9 · `leader` 2 ·
  `listed_unverified` 3 · `appears_on_screen` 1
- `subject_credit` — `found_in` (`personnel` 57 · `tracks` 9 · `prose` 3 · `none`
  3 · `her_discography_list_only` 8), `roles[]`, `note`, `raw[]`, the booleans
  `as_player` / `as_arranger` / `as_composer`, `needs_review`, and `review` (the
  judge's verdict on the 7 uncertain ones)
- `listed_in_her_discography`, `found_via`, `has_article`, `leader`, `year`,
  `musicbrainz` (41 have one; 38 have a sleeve in `shared/cover_art.json`)

`mentioned_only` lists 1 album article that names her without crediting her
(*Zodiac Suite*).

Per roster person: `album_count`, `albums[]`, `instruments[]`, `credit_type`,
`identified_via` (`wikilink` / `name_match` / `corpus_authority` /
`unidentified`), and the two joins: `said_about_subject` + `quotes[]`, and
`she_spoke_of_them` + `she_said`.

### `liston/own_interview.json` — the transcript

1,057 blocks in reading order: `speaker_role` is `subject` (521), `interviewer`
(524) or `none` (12). `people[]` on each block gives the names detected in it
with character offsets. Use it to render any exchange around a quote.

### `shared/class_of_1926.json`

Liston beside Coltrane and Davis: `she_said`, `direct_edge`, `shared_neighbours`,
`documents_naming_both`, `shared_releases`, `shared_roster`. She has a direct
network edge to Coltrane (they were in Gillespie's band together; `her_assent`)
and one shared release (*Art Blakey Big Band*, 1957). She never mentions Davis.

## 5. Ready-made facets

Closed vocabularies, already computed:

- `relation` (11 + `none`), `tier` (4), `contact_level` (6), `basis[]`
- `stance` positive / neutral / mixed / negative, `stance_strength` 0–3
- `notable` 0–3 — the ranking signal
- `her_words.basis` (5), `her_words.tie[]` (18)
- `own_voice.self.theme[]` (20), `own_voice.bryant.kind` (6), `liston_response` (5)
- `mention_kind` (11), `content_type[]` (17)
- `subject_role` (6), `subject_credit.found_in` (5)
- `collection`: Smithsonian (`si`), Hamilton, Rutgers — no Tulane interview
  names her
- `layers[]` on a person (4)

## 6. Media

**Portraits** — `shared/images.json`, 313 of 459 people (68%); 19 of the 20
witnesses and 53 of the 68 reconciled people she spoke of. Four sizes as stable
`Special:FilePath` URLs, the licence, the photographer, `attribution` ready to
print (211 require it), and `review_flags` (29 flagged, mostly
`may_be_a_group_photo`). Local 200px copies are in `img/p/<QID>.jpg`; hers is
also at `img/p/Q274146@2x.jpg`. `img/CREDITS.json` carries the terms with the
files.

**Sleeves** — `shared/cover_art.json`, 38 of the 41 releases with a MusicBrainz
release-group ID; copies in `img/a/<MBID>.jpg`. **Copyrighted**, supplied by the
Cover Art Archive for identification — see README §"Read this before building".

## 7. Things that will bite

1. **Filter before you render.** `witnesses`: drop `spoke_themselves == false`.
   `her_words`: drop `is_person == false`, and decide what to do with
   `basis in (bryant_only, transcriber_summary, none)`.
2. **`caution` on every witness row.** Not optional reading.
3. **Her quotes are short** — often a single sentence. `stands_alone:
   false` (in `own_voice.self`) means it needs `exchange` to make sense.
4. **`her_relationships.json` and `relationships.json` are the unjudged upstream
   model.** 59% wrong in her interview, 8 of 19 wrong about her witnesses. They
   are the audit trail; `her_words.json` and `witnesses.json` are the data.
5. **People without a QID dead-end** — no portrait, no link, no cross-layer join.
   That includes her mother, her husband, her teachers and her school friends:
   the people a centennial page may most want to show. Design the no-portrait
   state as a first-class state.
6. **`documents.json` has 20 items but she is in 25 interviews.** The 5 found by
   text search are in `text_hit_only_documents`, not `items`.
7. **Block text is verbatim, including transcription errors** — "enought",
   "Pigmeat Markum", "Dizzy's bandwidth me". `name` fields are corrected;
   quotes are not.

## Addendum: quote categories and the page bundle

- `own_voice.json` → `categories[]`: `key`, `label`, `order`, `definition`, and
  counts (`liston`, `bryant`, `liston_notable_2plus`). Ten sections, in page order.
- `own_voice.json` → `self.items[]` and `bryant.items[]` gain `category` (one
  key, always set), `category_secondary` (a second section the quote would be at
  home in; sparse), `category_agreed` (false where Pass C settled or overruled),
  `category_note` (Pass C's reason).
- `docs/data.json` is the page's own bundle (`hero`, `blurb`, `timeline`,
  `voices`, `own`, `discography`, `credits`), built by `site/build_site_data.py`.
  It is a projection of the files above plus `site/lanes.json` and
  `site/editorial.json`; nothing in it is judged afresh.
