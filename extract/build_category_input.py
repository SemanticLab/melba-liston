#!/usr/bin/env python3
"""Package the own-voice pull quotes for the category pass.

Writes liston/category_input.json: every pull quote in own_voice.json (hers and
Clora Bryant's), with the block it came from and the exchange around it, and
nothing that would lead the judge -- no theme, no notable grade, no stance.

The pass itself is Opus subagents working to extract/CATEGORY_SPEC.md; their
outputs land in liston/own_voice_output/category_*.json and are merged back into
own_voice.json by build_own_voice.py.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject as SUBJ  # noqa: E402

ROOT = Path(SUBJ.ROOT)
D = ROOT / SUBJ.KEY


def turns(ts):
    return [f'{t["speaker"]}: {t["text"]}' for t in ts]


def main():
    ov = json.loads((D / "own_voice.json").read_text(encoding="utf-8"))
    items = []
    for voice, key in (("liston", "self"), ("bryant", "bryant")):
        for i in ov[key]["items"]:
            e = {
                "block_id": i["block_id"],
                "voice": voice,
                "pull_quote": i["pull_quote"],
                "page": i["page"],
                "before": turns(i["exchange"]["before"]),
                "block_text": i["text"],
                "after": turns(i["exchange"]["after"]),
                "summary": i["summary"],
            }
            if voice == "liston":
                e["prompted_by"] = i["prompted_by"]
                e["period"] = i["period"]
            else:
                e["about"] = i["about"]
            items.append(e)
    items.sort(key=lambda e: e["block_id"])  # transcript order, both voices interleaved
    out = {
        "doc": ov["doc"],
        "read_this_first": ov["read_this_first"],
        "count": {"liston": ov["self"]["count"], "bryant": ov["bryant"]["count"]},
        "items": items,
    }
    (D / "category_input.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"category_input.json  {len(items)} pull quotes "
          f"(liston {out['count']['liston']}, bryant {out['count']['bryant']})")


if __name__ == "__main__":
    main()
