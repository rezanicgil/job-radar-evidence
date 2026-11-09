"""Report how a skill-presence baseline behaves on the matching pilot."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = re.compile(r"\b(?:Docker|JavaScript|Java|Kotlin|Python)\b", re.IGNORECASE)


def predict(requirement, passage):
    requested = {skill.casefold() for skill in SKILLS.findall(requirement)}
    mentioned = {skill.casefold() for skill in SKILLS.findall(passage)}
    if not requested:
        return "abstain"
    matches = requested & mentioned
    if matches == requested:
        return "supported"
    if matches and re.search(r"\b(or|veya)\b", requirement, re.IGNORECASE):
        return "supported"
    return "partial" if matches else "unverified"


def main():
    path = ROOT / "data" / "match_pilot.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    correct = 0
    false_support = 0
    for row in rows:
        predicted = predict(row["requirement"], row["cv_passage"])
        expected = row["label"]
        correct += predicted == expected
        false_support += predicted == "supported" and expected != "supported"
        print(f"{row['id']}: expected={expected} predicted={predicted}")
    print(f"Agreement: {correct}/{len(rows)}; false support: {false_support}")


if __name__ == "__main__":
    main()
