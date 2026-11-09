"""Collect a dated, deliberately limited English-language market report."""

from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BOARDS = ("commencis", "trendyol")
# Manually reviewed titles at these boards for the first snapshot.
TITLES = {"Senior Backend Engineer", "Data Engineer", "Data Science Professionals",
          "Data Scientist (Pre-Search)", "Software Engineer (Fintech Services)"}
SKILLS = ("Python", "Java", "SQL", "Docker", "Kubernetes", "Scala", "Kafka", "Spark")


def main():
    now = datetime.now(timezone.utc)
    postings = {}
    for board in BOARDS:
        url = f"https://api.lever.co/v0/postings/{board}?mode=json"
        with urlopen(url, timeout=30) as response:
            rows = json.load(response)
        for row in rows:
            if row.get("country") != "TR" or row["text"] not in TITLES:
                continue
            sections = [part["content"] for part in row["lists"]
                        if "qualification" in part["text"].casefold()]
            plain = unescape(re.sub(r"<[^>]+>", " ", " ".join(sections)))
            mentions = [s for s in SKILLS if re.search(rf"\b{s}\b", plain, re.I)]
            postings[row["hostedUrl"]] = dict(board=board, title=row["text"], skills=mentions,
                                               readable=bool(plain.strip()))
    report = ["# Türkiye software jobs · Pilot snapshot", "",
              f"Collected {now.isoformat(timespec='seconds')} UTC from two Lever boards.",
              "Scope: five manually selected technical titles, explicit TR location and eight tracked skill names.",
              "Counts reflect mentions in qualification sections, including optional or alternative skills.",
              "Each posting contributes at most once per skill. One collection cannot establish a trend.", ""]
    readable = [p for p in postings.values() if p["readable"]]
    report += [f"Readable qualification sections: {len(readable)} of {len(postings)} postings.", "",
               "| Skill | Postings mentioning skill | Distinct employers |",
               "| --- | ---: | ---: |"]
    for skill in sorted(SKILLS, key=lambda s: -sum(s in p["skills"] for p in readable)):
        matches = [p for p in readable if skill in p["skills"]]
        report.append(f"| {skill} | {len(matches)} / {len(readable)} | {len({p['board'] for p in matches})} |")
    report += ["", "## Source postings", ""]
    for url, p in postings.items():
        report.append(f"- [{p['board']} · {p['title']}]({url}) — " +
                      (", ".join(p["skills"]) or "No tracked mentions"))
    target = ROOT / "reports" / f"market-{now.date()}.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
