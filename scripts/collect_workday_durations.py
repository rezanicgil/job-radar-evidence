"""Collect duration passages from Workday detail pages of inventoried Türkiye software roles."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

from collect_duration_candidates import ROOT, extract_passages
from workday_board import posting_info

def read(job):
    info=posting_info(urlsplit(job["url"]))
    body=info.get("jobDescription")
    if not body or not body.strip():
        raise ValueError("Empty job description")
    return extract_passages(job,job["url"],[("description",body)])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory",type=Path,required=True)
    args=ap.parse_args()
    jobs={j["url"]:j for j in json.loads(args.inventory.read_text("utf8"))["jobs"]
          if j["areas"] and urlsplit(j["url"]).hostname.endswith(".myworkdayjobs.com")}
    failures={};rows={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url,f in {url:pool.submit(read,j) for url,j in jobs.items()}.items():
            try:
                for r in f.result(): rows[(url,r["text"])]=r
            except (OSError,ValueError,KeyError) as e: failures[url]=str(e)
    date=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest=ROOT/"data/raw"/("workday-duration-"+date);dest.mkdir(parents=True)
    out=list(rows.values())
    assert all(r["text"][m["start"]:m["end"]]==m["text"] for r in out for m in r["mentions"])
    path=dest/"candidates.jsonl";path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in out),"utf8")
    report=dict(collected_utc=date,inventory=args.inventory.name,attempted=len(jobs),readable=len(jobs)-len(failures),failures=failures,
                urls_with_mentions=len({r["source"] for r in out}),passages=len(out),unique_texts=len({r["text"].casefold() for r in out}),
                mentions=sum(len(r["mentions"]) for r in out),passages_by_employer=dict(Counter(r["employer"] for r in out)),
                sha256=sha256(path.read_bytes()).hexdigest(),reviewed_labels=0)
    (dest/"summary.json").write_text(json.dumps(report,indent=2)+"\n","utf8");print(dest,report)

if __name__=="__main__": main()
