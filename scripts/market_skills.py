"""Measure description-level technology mentions for a dated role inventory."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from hashlib import sha256
from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import workday_board

ROOT = Path(__file__).resolve().parents[1]
SKILLS = json.loads((ROOT / "releases/static-space/technologies.json").read_text(encoding="utf-8"))
PATTERNS = {s:re.compile(r"(?<![\w+#])"+re.escape(s)+r"(?![\w+#])",re.I) for s in SKILLS}
HEADINGS = {
    "qualifications": {"requirements","job requirements","qualifications","expected qualifications",
                       "qualifications & experience","what we're looking for","what you will need",
                       "what you'll bring","about your experience","aranan nitelikler","genel nitelikler","qualities we are looking for"},
    "preferences": {"nice to have","nice-to-have","nice to haves","preferred qualifications",
                    "preferred skills","bonus points","tercih edilen nitelikler","tercihen"},
}


def headed_sections(lists):
    sections=[]
    for item in lists:
        heading=item["text"].strip()
        normalized=" ".join(heading.replace("’","'").lower().rstrip(":?").split())
        kind=next((k for k,v in HEADINGS.items() if normalized in v),None)
        text=unescape(re.sub("<[^>]+>"," ",unescape(item["content"]))).strip()
        if kind and text:
            sections.append(dict(kind=kind,heading=heading,skills=[
                skill for skill,pattern in PATTERNS.items() if pattern.search(text)]))
    return sections


def lucida_sections(description):
    lists=[dict(text=heading.strip(),content=items)
           for heading,items in re.findall(r"<h3>([^<]*)</h3>\s*<ul>(.*?)</ul>",description,re.S|re.I)]
    return headed_sections(lists)


def crenno_sections(html):
    grouped={}
    kind=None
    for tag,body in re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>",html,re.I|re.S):
        text=" ".join(unescape(re.sub("<[^>]+>"," ",body)).replace("\u200b","").split())
        if tag.lower()=="p":
            heading=text.rstrip(":?").strip()
            if heading=="Ne arıyoruz":
                kind="qualifications"
            elif heading in {"Hangi ek beceriler öne çıkmana yardımcı olacak",
                             "Hangi ek beceriler öne çıkmanıza yardımcı olacak"}:
                kind="preferences"
            else:
                kind=None
            continue
        if kind and text:
            inline=re.search(r"\((tercih sebebi|artı değer olarak değerlendirilir)\)",text,re.I)
            key=("preferences",inline[1]) if inline else (kind,heading)
            grouped.setdefault(key,[]).append(text)
    return [dict(kind=k,heading=h,skills=[s for s,p in PATTERNS.items() if any(p.search(t) for t in items)])
            for (k,h),items in grouped.items()]


@lru_cache(maxsize=64)
def ashby_descriptions(board):
    request = Request(f"https://api.ashbyhq.com/posting-api/job-board/{board}",
                      headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)", "Accept":"application/json"})
    with urlopen(request, timeout=15) as response:
        jobs = json.load(response)["jobs"]
    return {row["jobUrl"]:row.get("descriptionPlain") or "" for row in jobs}


@lru_cache(maxsize=64)
def workable_descriptions(board):
    request = Request(f"https://www.workable.com/api/accounts/{board}?details=true",
                      headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)", "Accept":"application/json"})
    with urlopen(request, timeout=15) as response:
        jobs = json.load(response)["jobs"]
    return {row["shortcode"]:row.get("description") or "" for row in jobs}


def inspect(job, *, retry_timeout=True):
    url = urlsplit(job["url"])
    board, *rest = url.path.strip("/").split("/")
    key = rest[-1]
    if url.hostname == "jobs.lever.co":
        api = f"https://api.lever.co/v0/postings/{board}/{key}"
    elif url.hostname == "job-boards.greenhouse.io":
        api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{key}"
    elif url.hostname == "jobs.smartrecruiters.com":
        api = f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{key}"
    elif url.hostname.endswith(".bamboohr.com"):
        api = Request(job["url"] + "/detail", headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)", "Accept":"application/json"})
    elif url.hostname not in {"jobs.ashbyhq.com","apply.workable.com"} and not url.hostname.endswith(".myworkdayjobs.com"):
        return dict(**job,status="unsupported source")
    try:
        if url.hostname.endswith(".myworkdayjobs.com"):
            info=workday_board.posting_info(url)
            body=info["jobDescription"]
            job=dict(job,source_requisition=info.get("jobReqId"),source_listed_date=info.get("startDate"))
        elif url.hostname == "apply.workable.com":
            body = workable_descriptions(board)[key]
            if board=="lucida-ai":
                job=dict(job,sections=lucida_sections(body))
        elif url.hostname == "jobs.ashbyhq.com":
            body = ashby_descriptions(board)[job["url"]]
        else:
            with urlopen(api, timeout=15) as response:
                j = json.load(response)
        if url.hostname == "jobs.lever.co":
            job=dict(job,sections=headed_sections(j["lists"]))
            body = " ".join([j.get("descriptionPlain") or "", *(s["content"] for s in j["lists"]),
                             j.get("additionalPlain") or ""])
        elif url.hostname.endswith(".bamboohr.com"):
            opening = j["result"]["jobOpening"]
            if opening["jobOpeningName"].casefold() != job["title"].casefold():
                raise ValueError("Posting title changed since inventory")
            body = opening["description"]
        elif url.hostname == "job-boards.greenhouse.io":
            body = j["content"]
        elif url.hostname == "jobs.smartrecruiters.com":
            sections=j["jobAd"]["sections"]
            if board=="CRENNO":
                job=dict(job,sections=crenno_sections(sections.get("qualifications",{}).get("text","")))
            else:
                # SmartRecruiters has a dedicated qualifications field; never substitute
                # the job description or additionalInformation when it is missing.
                q=sections.get("qualifications") or {}
                if q.get("text","").strip():
                    job=dict(job,sections=headed_sections([dict(text="Qualifications",content=q["text"])]))
            body = " ".join(s.get("text","") for s in sections.values())
        plain = unescape(re.sub("<[^>]+>", " ", unescape(body)))
        if not plain.strip():
            return dict(**job,status="empty description")
        return dict(**job,status="readable",description_sha256=sha256(" ".join(plain.split()).encode()).hexdigest(),
                    skills=[s for s,p in PATTERNS.items() if p.search(plain)])
    except (URLError, TimeoutError, ValueError, KeyError) as exc:
        if retry_timeout and isinstance(getattr(exc,"reason",exc),TimeoutError):
            return inspect(job,retry_timeout=False)
        return dict(**job,status=str(exc))


def main(inventory=None):
    inventory = inventory or max((ROOT/"reports").glob("inventory-*T*.json"))
    folder = inventory.parent
    snapshot = json.loads(inventory.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(5) as pool:
        rows = list(pool.map(inspect,(j for j in snapshot["jobs"] if j["areas"])))
    readable = [r for r in rows if r["status"]=="readable"]
    now = datetime.now(timezone.utc)
    prefix = f"skill-mentions-{now:%Y-%m-%dT%H%M%S%fZ}"
    output = dict(inventory=inventory.name,collected_at=now.isoformat(),vocabulary=SKILLS,postings=rows)
    (folder / (prefix+".json")).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    lines = ["# Technologies mentioned in Türkiye software postings", "",
             f"Description retrieval: {now.isoformat(timespec='seconds')}. Inventory: [{inventory.name}]({inventory.name}).",
             f"Readable descriptions: {len(readable)} of {len(rows)} title-tagged postings.",
             f"Mentions include requirements, preferences and organization context. This snapshot tracks {len(SKILLS)} names.",
             "Counts use distinct posting URLs. A repeated mention contributes once per posting.",
             "", "| Technology | Postings | Employers |", "| --- | ---: | ---: |"]
    counts = [(s, [r for r in readable if s in r["skills"]]) for s in SKILLS]
    for skill, group in sorted(counts,key=lambda pair:-len(pair[1])):
        lines.append(f"| {skill} | {len(group)} / {len(readable)} | {len({r['employer'] for r in group})} |")
    lines += ["", f"[Posting URLs, area tags, retrieval failures and matched names]({prefix}.json)"]
    (folder / (prefix+".md")).write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines[:16]))
    print(prefix)
    return folder/(prefix+".json")


if __name__ == "__main__":
    main()
