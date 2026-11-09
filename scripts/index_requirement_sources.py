"""Index technical qualification bullets for review without publishing posting text."""

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.request import urlopen

from market_skills import ROOT, PATTERNS


def main():
    inventory=max((ROOT/"reports").glob("skill-mentions-*.json"))
    postings=json.loads(inventory.read_text(encoding="utf-8"))["postings"]
    cache=ROOT/"runs/requirement_sources"
    cache.mkdir(exist_ok=True)
    groups={}
    for job in postings:
        if not job["url"].startswith("https://jobs.lever.co/"):
            continue
        board,key=job["url"].split("/")[-2:]
        path=cache/(key+".json")
        if not path.exists():
            try:
                with urlopen(f"https://api.lever.co/v0/postings/{board}/{key}",timeout=10) as response:
                    sections=json.load(response)["lists"]
                path.write_text(json.dumps(sections,ensure_ascii=False),encoding="utf-8")
            except OSError as exc:
                print("Skipped",key,type(exc).__name__)
                continue
        for section in json.loads(path.read_text(encoding="utf-8")):
            if not re.search(r"qualif|requirement|looking for|will need|bring",section["text"],re.I):
                continue
            for i,bullet in enumerate(re.findall(r"<li\b[^>]*>(.*?)</li>",section["content"],re.I|re.S),1):
                text=" ".join(html.unescape(re.sub("<[^>]*>"," ",bullet)).split())
                names=[name for name,p in PATTERNS.items() if p.search(text)]
                if not names:
                    continue
                digest=hashlib.sha256(text.casefold().encode()).hexdigest()
                entry=groups.setdefault(digest,dict(fingerprint=digest,technologies=names,sources=[]))
                entry["sources"].append(dict(url=job["url"],employer=job["employer"],title=job["title"],
                                             section=section["text"].strip(),bullet=i))
    output=ROOT/"research/requirement_source_index.json"
    output.write_text(json.dumps(dict(snapshot=inventory.name,review_candidates=list(groups.values())),
                                 ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(len(groups),"unique candidate bullets")


if __name__=="__main__":
    main()
