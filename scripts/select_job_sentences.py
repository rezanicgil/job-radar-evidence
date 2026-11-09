"""Read an English job posting on stdin and print candidate skill sentences as JSON."""

import json
import re
import sys

from skill_sentence_baseline import ROOT, score


def main():
    sentences=[s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+",sys.stdin.read()) if s.strip()]
    if not sentences:
        raise SystemExit("Supply English job text on standard input.")
    path=ROOT/"releases/static-space/skill-sentences.json"
    model=json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps([s for s in sentences if score(s,model)>=model["threshold"]],
                     ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
