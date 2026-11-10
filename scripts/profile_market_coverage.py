"""Measure employer concentration within the latest local title inventory."""
from collections import Counter
from pathlib import Path
import json
from market_inventory import PATTERNS, ROOT, observation_date


def profile(path):
    data = json.loads(path.read_text("utf8"))
    groups = {area: {} for area in PATTERNS}
    classified = set()
    for job in data["jobs"]:
        for area in job["areas"]:
            groups[area][job["url"]] = job["employer"]
            classified.add(job["url"])
    lines = ["# Employer coverage by software role", "",
             f"Observed {observation_date(data['collected_at'])} (Türkiye time). Source: `{path.name}`.", "",
             f"{len(classified)} distinct posting URLs matched at least one tracked title category out of "
             f"{len({job['url'] for job in data['jobs']})} observed URLs. "
             "Categories can overlap. URLs do not identify unique vacancies across job boards.", "",
             "Largest employer share is the percentage of observed posting URLs in a category from its most represented employer. "
             "A high share makes that category sensitive to a single company's hiring. Zero means no matching title in this sample, not zero demand.", "",
             "| Role family | Posting URLs | Employers | Largest employer share |", "|---|---:|---:|---:|"]
    for area, jobs in sorted(groups.items(), key=lambda pair: (len(pair[1]), pair[0])):
        counts = Counter(jobs.values())
        share = f"{max(counts.values()) / len(jobs):.1%}" if jobs else "—"
        lines.append(f"| {area} | {len(jobs)} | {len(counts)} | {share} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    src = max((ROOT/"reports").glob("inventory-*.json"), key=lambda p: p.name)
    (ROOT/"reports/employer-coverage.md").write_text(profile(src), encoding="utf8")

