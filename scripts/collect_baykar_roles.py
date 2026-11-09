"""Inventory open software-related employment titles from Baykar's career board."""

from collections import Counter
from datetime import datetime, timezone
import json
import re
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

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
    report=dict(employer="Baykar",board_url=BOARD+"/tr/open-positions/",collected_at=now.isoformat(),
                scanned=total,source_types=types,location_status="Not provided by listing feed",
                postings=sorted(selected,key=lambda r:r["id"]))
    path=ROOT/"reports"/f"baykar-roles-{now:%Y-%m-%dT%H%M%SZ}.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(path.name,len(visited),total,types,len(selected))


if __name__=="__main__":
    main()
