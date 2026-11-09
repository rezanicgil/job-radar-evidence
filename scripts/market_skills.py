"""Measure description-level technology mentions for a dated role inventory."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("Python", "Java", "JavaScript", "TypeScript", "SQL", "PostgreSQL", "C++", "C#",
          "Kotlin", "Swift", "SwiftUI", "Jetpack Compose", "Flutter", "React", "Unity",
          "Docker", "Kubernetes", "Terraform", "Kafka", "Spark", "Simulink", "FreeRTOS",
          "STM32", "PyTorch", "AWS", "Azure", "Redis", "Linux", "Rust", "Git")
PATTERNS = {s:re.compile(r"(?<![\w+#])"+re.escape(s)+r"(?![\w+#])",re.I) for s in SKILLS}


def inspect(job):
    url = urlsplit(job["url"])
    board, *rest = url.path.strip("/").split("/")
    key = rest[-1]
    if url.hostname == "jobs.lever.co":
        api = f"https://api.lever.co/v0/postings/{board}/{key}"
    elif url.hostname == "job-boards.greenhouse.io":
        api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{key}"
    elif url.hostname == "jobs.smartrecruiters.com":
        api = f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{key}"
    else:
        return dict(**job,status="unsupported source")
    try:
        with urlopen(api, timeout=15) as response:
            j = json.load(response)
        if url.hostname == "jobs.lever.co":
            body = " ".join([j.get("descriptionPlain") or "", *(s["content"] for s in j["lists"]),
                             j.get("additionalPlain") or ""])
        elif url.hostname == "job-boards.greenhouse.io":
            body = j["content"]
        else:
            body = " ".join(s.get("text","") for s in j["jobAd"]["sections"].values())
        plain = unescape(re.sub("<[^>]+>", " ", unescape(body)))
        if not plain.strip():
            return dict(**job,status="empty description")
        return dict(**job,status="readable",skills=[s for s,p in PATTERNS.items() if p.search(plain)])
    except (URLError, TimeoutError, ValueError, KeyError) as exc:
        return dict(**job,status=str(exc))


def main():
    folder = ROOT / "reports"
    inventory = max(folder.glob("inventory-*T*.json"))
    snapshot = json.loads(inventory.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(5) as pool:
        rows = list(pool.map(inspect,(j for j in snapshot["jobs"] if j["areas"])))
    readable = [r for r in rows if r["status"]=="readable"]
    now = datetime.now(timezone.utc)
    prefix = f"skill-mentions-{now:%Y-%m-%dT%H%M%SZ}"
    output = dict(inventory=inventory.name,collected_at=now.isoformat(),postings=rows)
    (folder / (prefix+".json")).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    lines = ["# Technologies mentioned in Türkiye software postings", "",
             f"Description retrieval: {now.isoformat(timespec='seconds')}. Inventory: [{inventory.name}]({inventory.name}).",
             f"Readable descriptions: {len(readable)} of {len(rows)} title-tagged postings.",
             "Mentions include requirements, preferences and organization context. The fixed vocabulary tracks 30 names.",
             "Counts use distinct posting URLs. A repeated mention contributes once per posting.",
             "", "| Technology | Postings | Employers |", "| --- | ---: | ---: |"]
    counts = [(s, [r for r in readable if s in r["skills"]]) for s in SKILLS]
    for skill, group in sorted(counts,key=lambda pair:-len(pair[1])):
        lines.append(f"| {skill} | {len(group)} / {len(readable)} | {len({r['employer'] for r in group})} |")
    lines += ["", f"[Posting URLs, area tags, retrieval failures and matched names]({prefix}.json)"]
    (folder / (prefix+".md")).write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines[:16]))
    print(prefix)


if __name__ == "__main__":
    main()
