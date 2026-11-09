"""Inventory open software-related employment titles from Baykar's career board."""

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
import re
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

from market_inventory import ROOT, PATTERNS

BOARD="https://kariyer.baykartech.com"
API="/tr/basvuru/serializerProgram/"
EXTRA={
    "Embedded and firmware": r"gömülü|firmware",
    "Backend": r"arka uç|backend",
    "Frontend": r"ön (?:uç|yüz)",
    "Mobile (general/cross-platform)": r"mobil.*(?:yazılım|uygulama)",
    "Software engineering (general)": r"yazılım|software",
    "QA and testing": r"yazılım.*test|test.*yazılım",
    "Data and AI": r"yapay zek[aâ]|makine öğren|veri mühendisi",
}

def reviewed_qualifications(postings):
    specs=json.loads((ROOT/"data/baykar_qualifications.json").read_text(encoding="utf-8"))
    failures=[]
    for job in postings:
        chosen=[s for s in specs if s["id"]==job["id"] and s["url"]==job["url"]]
        if not chosen:
            continue
        try:
            with urlopen(Request(job["url"],headers={"User-Agent":"JobRadar/1.0"}),timeout=20) as response:
                page=response.read().decode("utf-8")
        except (URLError,TimeoutError,UnicodeError) as exc:
            failures.append(dict(id=job["id"],reason=type(exc).__name__))
            continue
        sections={}
        for heading,listing in re.findall(r'(Genel Nitelikler|Tercih Nedeni Olabilecek Ek Nitelikler)[: ]*(?:</[^>]+>\s*)+<ul[^>]*>(.*?)</ul>',page,re.I|re.S):
            sections[heading]=[" ".join(unescape(re.sub("<[^>]*>","",item)).split())
                               for item in re.findall("<li[^>]*>(.*?)</li>",listing,re.S)]
        for spec in chosen:
            items=sections.get(spec["section"],[])
            i=spec["bullet"]-1
            if not 0<=i<len(items) or sha256(items[i].encode()).hexdigest()!=spec["sha256"]:
                failures.append(dict(id=job["id"],section=spec["section"],bullet=i+1,reason="Source changed"))
                continue
            bucket="qualification" if spec["section"]=="Genel Nitelikler" else "preference"
            job.setdefault(bucket,[]).append(spec["condition"])
    return failures


def main():
    url=BOARD+API+"?page=1"
    visited=set()
    seen=set()
    types=Counter()
    selected=[]
    total=None
    while url:
        parsed=urlsplit(url)
        if parsed.scheme!="https" or parsed.netloc!=urlsplit(BOARD).netloc or parsed.path!=API or url in visited:
            raise ValueError("Unexpected pagination link")
        visited.add(url)
        with urlopen(Request(url,headers={"User-Agent":"JobRadar/1.0"}),timeout=20) as response:
            page=json.load(response)
        if total is not None and page["count"]!=total:
            raise ValueError("Source count changed during collection")
        total=page["count"]
        for row in page["results"]:
            if row["id"] in seen:
                raise ValueError("Repeated position during pagination")
            seen.add(row["id"])
            kind=row["type"]["text"]
            types[kind]+=1
            if kind!="İş" or not row["active"] or not row["visible"] or row["stop_application"]:
                continue
            title=row["text"].strip()
            areas={area for area,pattern in PATTERNS.items() if re.search(pattern,title,re.I)}
            areas.update(area for area,pattern in EXTRA.items() if re.search(pattern,title,re.I))
            if areas:
                selected.append(dict(id=row["id"],title=title,category=row["category"]["text"],
                                     areas=sorted(areas),url=BOARD+"/tr/acik-pozisyonlar/detay/"+quote(row["new_slug"])))
        url=page["next"]
    if len(seen)!=total:raise ValueError("Incomplete board inventory")
    now=datetime.now(timezone.utc)
    failures=reviewed_qualifications(selected)
    report=dict(employer="Baykar",board_url=BOARD+"/tr/open-positions/",collected_at=now.isoformat(),review_failures=failures,
                scanned=total,source_types=types,location_status="Not provided by listing feed",
                postings=sorted(selected,key=lambda r:r["id"]))
    path=ROOT/"reports"/f"baykar-roles-{now:%Y-%m-%dT%H%M%SZ}.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(path.name,len(visited),total,types,len(selected))


if __name__=="__main__":
    main()
