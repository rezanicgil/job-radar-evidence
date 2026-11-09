"""Measure Turkish suggestions against the labelled sections of five Roof Stacks postings."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

IDS={"49e4f4cb-430d-4f93-bbbe-c2556b20f79c","fde1267c-de8b-4361-901b-f99925f6b257",
     "22286111-d965-4644-804a-792504b559b0","70409613-03e9-48ba-a1f4-d96361a7b1f4",
     "31ea2349-542a-4661-b21c-fe5dedc09a06"}
HEADINGS=("Aranan Nitelikler","İletişim Becerileri","Takım Çalışması Beklentileri")


def index_sections(row):
    section=None
    index=[]
    source_hash=sha256(row["descriptionPlain"].encode()).hexdigest()
    for number,raw in enumerate(row["descriptionPlain"].splitlines(),1):
        line=" ".join(raw.split())
        if line in HEADINGS:
            section=line
        elif section and line:
            index.append(dict(source_url=row["hostedUrl"],title=row["text"],heading=section,line=number,
                              text_sha256=sha256(line.encode()).hexdigest(),posting_sha256=source_hash,
                              label="preference" if line.startswith("Tercihen") else "qualification"))
    return index


def check(url,rows):
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel="chrome")
        page=browser.new_page()
        page.goto(url)
        page.get_by_text("Find conditions in a job posting").click()
        page.locator("#postingLanguage").select_option("tr")
        for row in rows:
            text=row["descriptionPlain"]
            lines=[" ".join(line.split()) for line in text.splitlines() if line.strip()]
            if not all(heading in lines for heading in HEADINGS):
                raise ValueError("Employer headings changed. Recheck the source.")
            body=lines[lines.index(HEADINGS[0])+1:]
            expected={line:line.startswith("Tercihen") for line in body if line not in HEADINGS}
            page.locator("#posting").fill(text)
            page.locator("#suggest").click()
            choices=page.locator("#candidates input").evaluate_all("(xs)=>xs.map(x=>[x.value,x.dataset.preference==='true'])")
            found={" ".join(s.split()):value for s,value in choices}
            results.append(dict(url=row["hostedUrl"],source_sha256=sha256(text.encode()).hexdigest(),
                expected=len(expected),preferred=sum(expected.values()),
                correctly_typed=sum(found.get(s)==value for s,value in expected.items()),
                missed=len(expected.keys()-found.keys()),extra=len(found.keys()-expected.keys())))
        browser.close()
    return results


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="https://rezanicgil-job-radar-evidence.static.hf.space/")
    parser.add_argument("--cache",type=Path,help="Optional local cache of original Lever rows")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--index",type=Path,help="Export source pointers for the reviewed section lines")
    args=parser.parse_args()
    if args.cache:
        jobs=json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        response=requests.get("https://api.lever.co/v0/postings/roofstacks?mode=json",timeout=20)
        response.raise_for_status()
        jobs=response.json()
    sample=[r for r in jobs if r["id"] in IDS]
    if {r["id"] for r in sample}!=IDS:
        raise ValueError("A reviewed posting is unavailable")
    results=check(args.url,sample)
    args.output.write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    if args.index:
        args.index.write_text("".join(json.dumps(record,ensure_ascii=False)+"\n" for row in sample
                                      for record in index_sections(row)),encoding="utf-8")
    print({k:sum(r[k] for r in results) for k in ("expected","preferred","correctly_typed","missed","extra")})
