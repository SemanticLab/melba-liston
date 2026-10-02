# Category spec — sorting the own-voice pull quotes

Project root: `/Users/m/git/liston-centennial-2026`

Melba Liston (trombonist, arranger, composer; 1926–1999) gave one oral-history
interview: the Smithsonian Jazz Oral History Program, 4–5 December 1996, at her
home in Los Angeles. A centennial web page will be built from it. An earlier
reading pass pulled 256 short verbatim quotes out of that interview. The page
will show them in sections, and each quote has to sit in exactly one section.
This pass decides the sections and sorts the quotes into them.

## Read this before anything else

1. **Two voices.** 173 quotes are Liston's own (`voice: "liston"`). 83 are
   **Clora Bryant's** (`voice: "bryant"`): the interviewer, a trumpeter and a
   friend of decades, speaking about Liston to her face.
2. **Liston had a stroke in 1985.** She has memory loss and difficulty speaking.
   Her lines are short and plain. A short line is often only intelligible from
   the turn before it, so read `before` every time.
3. **Square brackets are the transcriber**, not a speaker.

## Your input

`liston/category_input.json` — `items[]`, in transcript order, both voices
interleaved:

| field | meaning |
|---|---|
| `block_id` | the key; unique across the whole file |
| `voice` | `liston` or `bryant` |
| `pull_quote` | the quote the page will show — **this is what you categorise** |
| `block_text` | the whole turn the quote was cut from |
| `before`, `after` | the turns around it, `Speaker: text` |
| `summary` | one sentence from the earlier pass saying what the line is about |
| `prompted_by`, `period` | (Liston) the question she was answering, and when in her life |
| `about` | (Bryant) what Bryant was speaking of |

Read the whole file before deciding anything.

## What a category is

A category is a **section of the page a reader would choose to open**. It is
about **subject matter** — what the line is about — not about tone, quality,
length, or who is speaking.

- **Between 8 and 12 categories.**
- **Every quote gets exactly one primary category.** No "other", no
  "miscellaneous", no catch-all for lines about her personality: a line that
  shows her character is still a line *about something* (the horn, a bandleader,
  being asked to remember), and it goes there.
- **Balance.** No category should hold more than about a fifth of Liston's
  quotes, and none should hold fewer than about eight of them. If a subject is
  too thin to stand, fold it into its nearest neighbour; if one is swallowing
  everything, split it.
- **Liston's lines decide the scheme.** Bryant's quotes are sorted into the same
  categories, so the page can set a peer's words beside hers, but do not create
  a category only Bryant's lines would fill.
- **Categorise the pull quote in its exchange**, not the whole block. If the
  block wanders over three subjects and the pull quote is about one, it is the
  one.
- **Subject over setting.** A line about writing an arrangement while on tour is
  about arranging if the writing is the point, and about the road if the travel
  is the point. Ask: what would a reader who opened this section expect to find?
- A **secondary** category is allowed when a quote would be equally at home in
  a second section. Use it sparingly — fewer than a third of quotes.

---

## Pass A — design the scheme

Write `liston/own_voice_output/category_scheme.json`:

```json
{
 "categories": [
  {
   "key": "snake_case_key",
   "label": "One to three words, as a section heading",
   "definition": "One or two sentences: what belongs here.",
   "includes": ["kinds of line that belong", "..."],
   "excludes": ["kinds of line that look as if they belong but go elsewhere, and where"],
   "expected_liston": 0,
   "expected_bryant": 0
  }
 ],
 "order_rationale": "Why the categories are in this order.",
 "boundary_rules": [
  "When a line is both X and Y, it goes to ... because ..."
 ],
 "notes": "Anything the sorters need to know."
}
```

- `categories` is in the **order the page should show them**.
- `label` is what a visitor reads. Plain words; no colons, no puns.
- `includes` / `excludes` describe **kinds** of line. Do **not** cite block ids
  or quote the input: two readers will sort the quotes independently from your
  definitions, and examples drawn from the data would decide their answers for
  them.
- `boundary_rules` are where the work is. Find every pair of categories a line
  could fall between and say which way it goes.
- `expected_*` are your rough counts, so the balance rule can be checked.

Before you finish, walk the whole input once more against your scheme and
confirm that every quote has one clear home.

---

## Pass B — sort the quotes

You are given the scheme (`liston/own_voice_output/category_scheme.json`). You
may not change it. Write the file named in your instructions:

```json
{
 "items": [
  {
   "block_id": 0,
   "category": "key",
   "secondary": "key or null",
   "confidence": "high | medium | low",
   "reason": "A short clause: why this section. Required when confidence is not high or a boundary rule decided it."
  }
 ],
 "scheme_problems": ["Any quote kinds the scheme has no clear home for, or rules that conflict."]
}
```

- One entry for **every** `block_id` in the input — all 256.
- `category` and `secondary` must be keys from the scheme. `secondary` is null
  unless the quote is equally at home in a second section.
- Work from the definitions and boundary rules, quote by quote. Do not sort by
  page position or by what the neighbouring quotes got.

---

## Pass C — settle the disagreements

Two readers sorted the quotes independently. You are given the scheme, the
input, and `liston/own_voice_output/category_disagreements.json` — the quotes
where their primary categories differ, each with both readers' answers and
reasons. For each, read the quote in its exchange and decide. You may choose
either reader's answer or, rarely, a third category.

The two readers work from the same boundary rules, so they can agree on a quote
and both be uneasy about it. Pass C therefore also reviews every quote that
either reader marked below `high` confidence or named in `scheme_problems`
(`category_a.json`, `category_b.json`). For those the test is the one the
scheme itself sets — *what would a reader who opened this section expect to
find?* — and a boundary rule that sends a line somewhere its own words do not
belong may be overruled for that line. Leave a quote out of your output if the
readers' answer should stand; include it only to change the primary category
(`sided_with: "neither"`).

Write `liston/own_voice_output/category_adjudicated.json`:

```json
{
 "items": [
  {
   "block_id": 0,
   "category": "key",
   "secondary": "key or null",
   "sided_with": "a | b | neither",
   "reason": "One sentence."
  }
 ],
 "scheme_problems": ["Patterns in the disagreements that point at a fault in the scheme."]
}
```
