#!/bin/sh
# Rebuild every deterministic layer, in dependency order.
#
# The judgement passes are NOT run from here -- they are Claude Opus subagents
# working to the specs in extract/*_SPEC.md, and their outputs are checked into
# the tree:
#     liston/eval_output/chunk_*.json       (EVAL_SPEC.md)
#     liston/recovered_output.json          (RECOVERED_SPEC.md)
#     liston/her_words_output/chunk_*.json  (HER_WORDS_SPEC.md)
#     liston/own_voice_output/*.json        (OWN_VOICE_SPEC.md)
#     liston/own_voice_output/category_*.json (CATEGORY_SPEC.md; input from
#                                            extract/build_category_input.py)
#     liston/witness_output.json            (WITNESS_SPEC.md)
#     discography/raw/credit_review_output.json
# Each "-> judge" comment below marks where a pass reads the files just built.
# If an input changes, the pass must be re-run before the merge step after it.
set -e
cd "$(dirname "$0")"

# ---- transcript layers (stdlib only; read-only on linked_jazz.sqlite)
uv run python extract/build_profile_docs.py      # profile / documents / cooccurrence
uv run python extract/build_quotes.py            # every block that may be about her
uv run python extract/build_relationships.py     # upstream relations: others -> her
uv run python extract/build_connections.py       # network edges, communities
uv run python extract/build_nicknames.py         # raw text sweep (recall audit)
uv run python extract/build_context.py           # -> judge: liston/eval_input/
uv run python extract/build_own_interview.py     # -> judge: her_words_input/, own_interview.txt
uv run python extract/build_answers.py           # recovered candidates
uv run python extract/build_continuations.py
uv run python extract/build_recovered_threads.py # -> judge: recovered_input.json

# ---- merge the judgement
uv run python extract/build_enriched.py          # enriched / best_quotes / false_positives
uv run python extract/merge_recovered.py         # recovered_evaluated / recovered_best
uv run python extract/build_her_words.py         # her_words.json
uv run python extract/build_own_voice.py         # own_voice.json

# ---- discography (network; everything cached under discography/cache/)
uv run python discography/harvest_discographies.py
uv run python discography/resolve_entities.py
uv run python discography/fetch_album_pages.py
uv run python discography/parse_albums.py
uv run python discography/resolve_personnel.py
uv run python discography/build_discography.py   # needs enriched.json + her_words.json
                                                 # -> judge: raw/credit_review_input.json

# ---- witnesses and the people index
uv run python extract/build_witness_input.py     # -> judge: witness_input.json
uv run python extract/build_witnesses.py         # witnesses.json (no portraits yet)
uv run python discography/build_images.py        # shared/images.json
uv run python discography/fetch_cover_art.py     # shared/cover_art.json
uv run python discography/fetch_local_images.py  # img/
uv run python extract/build_witnesses.py         # again, now with portraits; people.json
uv run python extract/build_class_of_1926.py     # shared/class_of_1926.json

# ---- the gate
uv run python extract/verify_all.py

# ---- the page bundle (docs/ is what GitHub Pages serves)
uv run python site/build_site_data.py            # docs/data.json, docs/img/
