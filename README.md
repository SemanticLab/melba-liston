# Melba Liston — centennial data extraction

What jazz musicians said about **Melba Liston** (13 January 1926 – 23 April
1999; trombonist, arranger, composer) — and what she said about them — pulled
from the Linked Jazz 2026 corpus for her 2026 centennial.

**This repo is the data layer only.** The web page comes later; nothing here
renders anything.

It is a port of the Coltrane / Davis build (`~/git/linked-jazz-coltrane-davis`,
published as `~/git/centennial-2026`): same corpus, same conventions, same
passes. Where it departs from that build, it is because of one fact — see the
next section.

Source: `~/git/ch-jazz-mashup/linked_jazz.sqlite` — 1,347 oral-history interview
transcripts from four archives (Tulane/Hogan, Hamilton/Fillius,
Smithsonian/NEA Jazz Masters, Rutgers/IJS). The DB is opened read-only
everywhere and is never modified.

## The one thing that makes her different

**Coltrane and Davis were never interviewed. Liston was.** The Smithsonian Jazz
Oral History Program recorded her on 4–5 December 1996 at her home in Los
Angeles; the interviewer was the trumpeter **Clora Bryant**, a contemporary and
friend. So where the earlier build could only look one way — what other people
said about the subject — this one looks three ways:

| direction | where | size |
|---|---|---|
| **others → her** | 24 other interviews | 49 blocks about her, 20 people who actually spoke |
| **her → others** | her own interview | 106 people, 66 with a line in her own words |
| **her → herself** | her own interview | 173 lines, 53 timeline facts |
| *(and Bryant → her, to her face)* | her own interview | 83 lines |

The first row is the whole of what the earlier build had, and for Liston it is
**small**: she is named in 24 interviews against Coltrane's 299. The centennial
page will lean on the other three.

Two properties of her interview shape everything downstream:

- **She had a stroke in 1985.** Eleven years later she has memory loss and
  difficulty speaking. Her turns are short — many are a bare "Yeah." — and Bryant,
  who knows her life, often *tells* it and lets her confirm.
- **Square brackets are the transcriber.** Where she could not answer, the
  transcriber substituted a summary: *"[Liston cannot recall what happened
  next.]"*. Those are never her words. **No quote attributed to her anywhere in
  this repo contains one** (checked programmatically, see `verify_all.py`).

## Layout

```
liston/
  profile.json               identity, links, community, headline stats
  documents.json             the interviews that name her (+ text_hit_only_documents)
  --- others -> her ---
  quotes.json                every block that may be about her, with context
  relationships.json         upstream LLM relations to her (19; weak -- see witnesses.json)
  connections.json           network edges to every other person (123)
  cooccurrence.json          entities named in the same block (her own interview excluded)
  nicknames.json             raw text sweep for Melba / Liston -- the recall audit
  eval_input/ eval_output/   chunks to and from the block-level judgement
  enriched.json              ★ every block: window + judgement + provenance
  best_quotes.json           ★ the verbatim-checked display shortlist (21)
  false_positives.json       blocks judged not about her (1)
  recovered_*.json           pronoun follow-ons and answers; recovered_best.json ★ (2)
  witness_input/output.json  bundles to and from the person-level judgement
  witnesses.json             ★ one row per witness: relation, caption, lead quote, caution
  --- her -> others, her -> herself ---
  own_interview.json         her whole interview, block by block, roles resolved
  own_interview.txt          the same as reading text (what the judges read)
  own_interview_entities.json  places, bands, tunes, venues named in it (raw NER)
  her_relationships.json     upstream LLM relations FROM her (115; 59% wrong -- see below)
  her_words_input/ output/   chunks to and from that judgement
  her_words.json             ★ one record per person she spoke of, judged
  own_voice_output/          raw reading-pass output
  own_voice.json             ★ self (173) · bryant (83) · timeline (53)
  --- records ---
  discography.json           ★ 80 releases with her credit on each
  discography_personnel.json ★ 582 people on those records + the two-way interview join
  --- everyone ---
  people.json                ★ one record per person across all four layers (487)
shared/
  images.json                ★ portrait per person: Commons URLs, licence, attribution
  cover_art.json             album sleeves from the Cover Art Archive (38)
  communities.json           all 58 network communities; 2 is hers
  class_of_1926.json         her beside Coltrane and Davis, the other 1926 centennials
  *_summary.json             stats for each pass
img/
  p/<QID>.jpg                314 portraits (200px; hers also @2x)
  a/<MBID>.jpg               38 sleeves
  CREDITS.json               licence + attribution for every file
extract/                     transcript-derived layers (stdlib only) + the five SPEC.md files
discography/                 Wikipedia / Wikidata / Commons layers; cache/ and raw/
build_all.sh                 every deterministic step, in order
```

★ = what a page should read. Everything else is working material or audit trail.
`DATA_MODEL.md` describes the starred files field by field.

## How the judgement was done

Every decision that needs reading — is this block about her, what did she say
about this person, which line leads — was made by **Claude Opus 5.5 subagents**,
each working to a written spec in `extract/`. The earlier build used a mix of
subagents, Gemini and a local Qwen for the same jobs; here it is one model
throughout. Twelve agent runs in all:

| pass | spec | agents | input → output |
|---|---|---|---|
| block evaluation | `EVAL_SPEC.md` | 3 | 118 blocks in windows → `eval_output/` |
| recovered blocks | `RECOVERED_SPEC.md` | 1 | 22 pronoun/answer blocks → `recovered_output.json` |
| her words | `HER_WORDS_SPEC.md` | 4 | 117 detected "people" → `her_words_output/` |
| own voice | `OWN_VOICE_SPEC.md` | 2 | the whole transcript → `own_voice_output/` |
| witnesses | `WITNESS_SPEC.md` | 1 | 25 bundles → `witness_output.json` |
| album credits | *(in the prompt)* | 1 | 7 uncertain credits → `raw/credit_review_output.json` |

The her-words and own-voice readers each read **the entire transcript** (1,057
blocks, ~125k characters) before judging anything, which is what the windowed
approach of the earlier build could not do: an answer on page 40 can settle a
question from page 9.

**No judge's quote is trusted.** Every merge script re-verifies every quote as an
exact substring of one source block, spoken by the right voice, outside any
transcriber bracket, and drops what fails. `extract/verify_all.py` then re-does
the whole check independently against the database rather than the intermediate
JSON: **698 quotes checked, 0 failures**, and no quote had to be dropped at any
merge step.

Merges of duplicate people (five of them) were recommended by the readers and
are recorded with their reasons in `build_her_words.py` → `MERGES`; the absorbed
records are kept under `her_words.json` → `merged`.

## The numbers

| | |
|---|---|
| interviews naming her (other than her own) | **24** — 19 reconciled to her QID + 5 found only by text search |
| blocks about her in those interviews | **49** of 50 evaluated (1 false positive) |
| …where the wider context changed the reading | 44% of all 118 evaluated blocks |
| people who said something about her in their own words | **20** (21 interviews; Slide Hampton twice) |
| display shortlist (`best_quotes.json`) | **21** — 12 from other interviews, 9 Clora Bryant |
| recovered pronoun/answer blocks really about her | 5 of 22 (23%) |
| people named in her own interview | 117 detected → **106 real people** after judgement |
| …with a relation established | 84 |
| …with a line in her own words | **66** (156 verified quotes) |
| her lines about herself | **173** (12 at the top grade) |
| Clora Bryant's lines about her | **83** (8 at the top grade) |
| biographical timeline entries | 53 (44 confirmed by Liston) |
| releases | **80** — 72 with an article, 8 listed without one |
| …credited as player / arranger-conductor / composer | 41 / 24 / 18 |
| people credited on those records | 582 (416 with a QID) |
| …who were interviewed in the corpus | 86 |
| …and said something about her | **10** |
| …whom she spoke of | **36** |
| people with a portrait | 313 of 459 (68%); 19 of the 20 witnesses |
| network edges | 123 (72 to reconciled people) |

**Eight people appear in both directions** — they spoke of her and she spoke of
them: Randy Weston, Slide Hampton, Gerald Wilson, Clora Bryant, Al Grey, Abbey
Lincoln, Benny Powell, Vi Redd. Five of those are also on her records and in the
network — all four layers: Weston, Hampton, Grey, Lincoln, Powell.

## What came out of it

**The upstream model was wrong about her interview more often than it was
right.** Of 113 relations it classified *from* her, the readers judged **67
wrong (59%)**. The cause is the stroke: she answers "Yeah.", so the model took
what Bryant said for what Liston said. It also typed 16 non-people as people —
six tune titles (*Little Niles*, *Len Sirrah*, *Pam's Waltz*, *Ben Loves Lu*…),
a playground, an insurance company, "Saxophone player". `her_relationships.json`
is kept as the audit trail; **use `her_words.json`**, and filter on `basis`:

| `basis` | meaning | people |
|---|---|---|
| `her_statement` | she said it, in her own words | 53 |
| `her_assent` | Bryant said it, she agreed — the words are in `bryant_quote` | 16 |
| `transcriber_summary` | only a bracketed summary supports it | 14 |
| `bryant_only` | Bryant said it; Liston did not confirm | 7 |
| `none` | no relation established | 16 |

**The name-matching missed a fifth of the interviews that mention her.** Only 40 blocks outside her
own interview reconcile to her QID. A text search for a bare "Melba", "Liston,
Melba" and "Melvin Liston" (`extract/subject.py`) found 10 more blocks in 5
interviews the person layer had not linked at all — **Mary Lou Williams, Quincy
Jones, Shirley Horn, Von Freeman, J.C. Higginbotham** — and the evaluators
confirmed all 10 as her. Williams's is one of the best passages in the set.

**She deflects praise.** Of Bryant's 83 remarks, Liston elaborates on 32,
confirms 17, **deflects 16 and denies 10**. Bryant: *"that is one of the most
beautiful things you've ever done"* — Liston: *"I don't know."* That pattern is
in `own_voice.json` → `bryant[].liston_response` with the reply text alongside.

**Her own top lines** (`own_voice.json` → `self`, `notable: 3`):

> "I just loved the instrument. I didn't need no inspiration."
>
> "I do it all from my soul, and if it sounds like somebody, well it sounds like
> somebody. It's my inspiration. It's from my soul."
>
> "I'm a woman. That's that."
>
> "But blowing, I don't think about nothing but the notes."
>
> "I'm sorry that I couldn't talk more."

**What the witnesses said** (`witnesses.json`, top of the list):

> "She played really good, and she wrote music that weighs as much as this
> building." — Slide Hampton
>
> "Then I realized that only Melba Liston could do this." — Randy Weston
>
> "you have been the best, Melba. You've been a guiding light for a lot of people,
> including me" — Clora Bryant

**Her discography is an arranger's.** Her own Wikipedia article lists 63 records,
filed as "sidewoman or guest". Sweeping the album articles that *link* to her
found 17 more that her list omits — records she wrote for rather than played on
(*White Gardenia*, *For the First Time*, *Hub Cap*, *When I'm Alone I Cry*), and
nine where someone else recorded her tunes. `subject_credit` on every release
says where the credit was found and what it is.

## Read this before building the page

1. **Every witness row carries a `caution`.** All 25. Read them. Examples that
   would mislead if displayed bare: Shirley Horn's *"a great jazz artist"* is
   followed at once by *"there are certain instruments I think a woman does not
   have the strength to play"* — the row's stance is `mixed`. Abbey Lincoln's
   *"It's a rare woman, like Melba Liston, who comes to the music for the music"*
   sits inside a put-down of women musicians generally (`stance_target:
   women_in_jazz`). Curtis Fuller says Gerald Wilson was her husband — the judge
   flagged that as doubtful and nothing else in the corpus supports it.
2. **`spoke_themselves: false` is not a witness.** Four rows: Quincy Jones, Hank
   Jones, Paul Howard, and the Snooky Young / Gerald Wilson joint interview. In
   each her name is in the interviewer's mouth or the archive's front matter. In
   the Quincy Jones transcript every claim about her (that she wrote *Reverie*
   for his band, that she inspired the women of Diva) is the *interviewer's*,
   David Baker's — do not present it as Jones's testimony.
3. **One witness is not the interviewee.** In the Clark Terry interview the man
   talking about Liston is the co-interviewer, singer **Joe Williams**; Terry
   says nothing about her. The row is Williams's.
4. **Bryant's facts are Bryant's.** She supplies dates and events from memory and
   from notes, and Liston often cannot confirm or flatly denies them (recording
   with Basie; the Ellington influence). Timeline entries with `stated_by:
   "bryant"` and `confirmed_by_liston: false` are not her testimony.
5. **`documents.interviewee` is wrong for two of her witnesses.** The Teddy
   Edwards and Paul Howard transcripts both name the interviewer, Patricia
   Willard, as interviewee. `witnesses.json` → `name` is right; `enriched.json`
   → `doc.interviewee_field` is not. Several Smithsonian names are stored
   surname-first ("Akiyoshi Toshiko", "Horn Shirley").
6. **Some of the best lines are not quotable.** Quentin Jackson's *"a great
   trombonist, too"* and Higginbotham's *"She can play, too, boy"* sit in blocks
   that do not name her, outside any judged block, so the verbatim rule could
   not admit them. The evaluators recorded them in `notes` and `summary`.
7. **Four people in her interview still need splitting by hand** — see
   `her_words.json` → `unmerged_leads`. The main one: the detected "Minnie
   Hightower" folds a schoolmate with her mother, the teacher (Alma Hightower,
   who led the Melodic Dots). The record describes the mother; "Alma" is not in
   the transcript and was supplied by a reader.
8. **Sensitive material exists.** She describes a bandmate coming into her hotel
   room on the road (block 295771; her line *"that's what girls have to go
   through"* is in the next block), and Randy Weston's account of getting her to
   write again after the stroke includes *"I insulted her… called her all kinds
   of names"*. Both are flagged in `notes` / `caution`, not filtered.
9. **The discography is "what Wikipedia documents", not a sessionography.**
   Three records her own article lists are not credited to her on the album's
   page (`subject_role: "listed_unverified"`): *At Basin Street East*, *Mary Lou
   Williams*, *That Lovin' Feelin'*. Eight more have no article at all. Release
   `kind` is mostly the generic `album` — her article has no studio/live split.
10. **A composer credit is not a session.** Nine releases carry her only on a
    track line (`subject_role: "composer"`) — someone recorded *Just Waiting* or
    *Melba's Blues*. She was not necessarily in the studio.
11. **Check `review_flags` before using a portrait large**, and print
    `attribution` — 211 images require it. 49 are Linked Jazz thumbnails with no
    licence metadata (`not_commons_licence_unverified`).
12. **Cover art is not free.** 38 sleeves from the Cover Art Archive are in
    `img/a/`, copyrighted and supplied for identification. Using them was an
    explicit editorial call in the Coltrane / Davis build; it is carried over
    here on the same terms and should be re-decided before publishing.
13. **Confidence is useless for ranking; `notable` is quota'd per chunk.** Same
    as the earlier build. Rank by `notable`, then relation weight.
14. **A Wikidata duplicate.** The corpus authority file holds `Quentin "Butter"
    Jackson` = `Q99676854`, a bare item with no dates or article, beside the real
    Quentin Jackson `Q720707`. Witness rows resolve to `Q720707`; the roster
    still carries one credit under the stub. Worth merging upstream.

## The page

`docs/` is the site, laid out for GitHub Pages ("deploy from branch", folder
`/docs`). It follows the design in the claude.ai/design project *Melba Liston
Centennial Page*: hero, Wikipedia blurb and links, timeline, what people said,
her own words, discography.

| file | what |
|---|---|
| `docs/index.html`, `style.css`, `app.js` | the page: static, hand-written, no framework, no build step |
| `docs/data.json` | everything the page shows, built by `site/build_site_data.py` |
| `docs/transcripts.json` | the transcript text behind every quote, shown in a popup: her interview whole, each witness's interview as a window (10–16 turns either side) around the quoted turn, each with the archive's own URL. The page does not link to the transcript reader. Built by the same script, from `linked_jazz.sqlite` |
| `docs/img/p/`, `docs/img/a/` | only the portraits and sleeves the page uses, copied from `img/` |
| `docs/img/liston.png`, `linked-jazz.png` | the design's own two images (not generated) |
| `site/lanes.json` | the career bars above the timeline dots, hand-authored, each with its `source` |
| `site/editorial.json` | display decisions the data cannot make by rule: the tagline, and per-witness hide / second quote / context note, each with the `caution` it follows from |

```sh
uv run python site/build_site_data.py          # after any change under liston/
cd docs && uv run python -m http.server 8765   # preview (data.json is fetched, so file:// will not do)
```

What the page does with the cautions above: a witness gets a card only if they
spoke themselves and have a verbatim lead quote: 17 of the 24 people in
`witnesses.json`. Quincy Jones, Hank Jones, Paul Howard and Snooky Young never
speak of her themselves, Maxine Sullivan and Hayes Pillars have no quotable
line, and Higginbotham is hidden by `editorial.json`. Timeline dots are the
interview's own 53 entries; the 22 she gave no year for are placed between their
dated neighbours and drawn grey. A line of hers that needs its question
(`stands_alone: false`) is shown with the reading pass's one-sentence summary
under it.

### "Who was on the records"

Inside the Discography section. Counted only on the 67 releases she played on,
arranged or led (a composer credit is not a session): 464 named musicians, 176
on more than one, 22 on eight or more. The page lists everyone on three or more
plus anyone with words in either direction (123 people). Nine spoke of her
(their card is the same vetted quote as in "What people said"); she spoke of 23
(`her_words.json`, only `her_statement` and `her_assent`; where she only agreed,
the reading pass's summary is shown beside or in place of a quote). The six she
recorded with most often (Clark Terry, Jerome Richardson, Jimmy Cleveland, Ernie
Royal, Joe Newman, Phil Woods) are in neither group, though three of them have
oral histories in the corpus. Choosing a person filters the release grid to the
records they share. Portraits flagged `not_commons_licence_unverified` or
`picked_from_category_not_curated` are not used (the latter gave Oliver Nelson a
photograph of a car).

### Sections of "In her own words"

Every pull quote in `own_voice.json` (173 hers, 83 Bryant's) carries a
`category`: one of ten page sections, listed in `own_voice.json` →
`categories`. The pass is `extract/CATEGORY_SPEC.md`: one Opus subagent designed
the scheme from the quotes, two sorted all 256 independently, a fourth settled
the one quote they split on and reviewed the 32 others either had doubts
about, overruling the scheme's rules on two. The two sorters agreed on 255 of 256, but
that measures how tightly the scheme's 26 boundary rules are written, not how
obvious the sections are. The older multi-label `theme` is still on each item.

## Rebuilding

```sh
./build_all.sh        # every deterministic step, then the verification gate
```

It is safe to re-run: the Wikipedia/Wikidata/Commons responses are cached under
`discography/cache/`, images already on disk are skipped, and the judgement
outputs are read from the tree. The script's comments mark where each judgement
pass reads its input; if one of those inputs changes, that pass has to be re-run
(a subagent, the spec, the input file) before the merge step after it.

## What was not ported

`build_site_data.py` and `build_site.py` — the page bundle and the page — are
presentation and were left out on purpose. Three scripts they depended on are
replaced rather than ported: `reclassify_knows_of.py` and `gen_one_liners.py`
(local Qwen) and `classify_recovered_gemini.py` (Gemini) are now the witness and
recovered passes above. `shared/coltrane_davis.json`, the two-subject bridge, has
no equivalent with one subject; `shared/class_of_1926.json` is the nearest thing
— Liston beside the other two 1926 centennials, including the one piece of
direct evidence that build could not have: asked whether John Coltrane was in
Dizzy Gillespie's band when she joined, she said yes.
