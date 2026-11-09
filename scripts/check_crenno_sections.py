"""Check Turkish posting suggestions against seven indexed CRENNO qualification sections."""
import argparse
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re

import requests
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
IDS=["744000127863239","744000127843364","744000127842769","744000109940251","744000109926925","744000109920915","744000096398625"]


def plain(html):
    return " ".join(unescape(re.sub("<[^>]+>"," ",html)).replace("\u200b","").split())


def extract(job):
    sections=job["jobAd"]["sections"]
    lines=[]
    expected={}
    references=[]
    for name,section in sections.items():
        lines.append(section["title"])
        kind=None
        for i,(tag,body) in enumerate(re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>",section["text"],re.I|re.S),1):
            line=plain(body)
            if not line:
                continue
            lines.append(line)
            if name!="qualifications":
                continue
            if tag=="p":
                if line=="Ne arıyoruz?":
                    kind="qualification"
                elif line.startswith("Hangi ek beceriler"):
                    kind="preference"
                continue
            if tag=="li" and kind:
                optional=kind=="preference" or "(tercih sebebi)" in line or "(artı değer olarak değerlendirilir)" in line
                expected[line]=optional
                references.append(dict(source_url="https://jobs.smartrecruiters.com/CRENNO/"+job["id"],
                    block=i,text_sha256=sha256(line.encode()).hexdigest(),section=kind,expected_optional=optional))
    if not references:
        raise ValueError("Qualification structure has changed")
    return "\n".join(lines),expected,references


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("url")
    cli.add_argument("output",type=Path)
    cli.add_argument("--index",type=Path)
    args=cli.parse_args()
    results=[]
    refs=[]
    with sync_playwright() as p:
        b=p.chromium.launch(channel="chrome")
        page=b.new_page()
        page.goto(args.url)
        page.get_by_text("Find conditions in a job posting").click()
        page.locator("#postingLanguage").select_option("tr")
        for key in IDS:
            r=requests.get("https://api.smartrecruiters.com/v1/companies/CRENNO/postings/"+key,timeout=15)
            r.raise_for_status()
            text,expected,source=extract(r.json())
            refs.extend(source)
            page.locator("#posting").fill(text)
            page.locator("#suggest").click()
            found=dict(page.locator("#candidates input").evaluate_all("(xs)=>xs.map(x=>[x.value,x.dataset.preference==='true'])"))
            results.append(dict(id=key,input_sha256=sha256(text.encode()).hexdigest(),expected=len(expected),optional=sum(expected.values()),
                correct=sum(found.get(s)==v for s,v in expected.items()),missed=len(expected.keys()-found.keys()),
                wrong_type=sum(found[s]!=expected[s] for s in expected.keys()&found.keys()),
                extra=len(found.keys()-expected.keys())))
        b.close()
    totals={k:sum(r[k] for r in results) for k in results[0] if isinstance(results[0][k],int)}
    print(totals)
    args.output.write_text(json.dumps(dict(totals=totals,postings=results),indent=2)+"\n","utf8")
    if args.index:
        args.index.write_text("".join(json.dumps(row)+"\n" for row in refs),"utf8")


if __name__=="__main__":
    main()
