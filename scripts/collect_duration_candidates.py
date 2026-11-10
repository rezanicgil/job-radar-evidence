"""Collect unlabeled duration mentions for private review, restricted to inventoried Turkish roles."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
import requests

ROOT=Path(__file__).resolve().parents[1]
DURATION=re.compile(r"(?<!\w)(?:\d+(?:\s*[-–]\s*\d+)?\+?|one|two|three|four|five|six|bir|iki|üç|dört|beş|altı)\s*[- ]?\s*(?:years?|months?|weeks?|days?|yıl(?:lık)?|sene|ay(?:lık)?|hafta|gün)\b",re.I)

def extract_passages(job,url,sections):
    rows=[]
    for heading,body in sections:
        plain=unescape(re.sub('<[^>]+>',' ',re.sub(r'</(?:li|p|div)>|<br\s*/?>','\n',body or '',flags=re.I)))
        for line in re.split(r'\n|(?<=[.!?])\s+',plain):
            line=' '.join(line.split())
            matches=list(DURATION.finditer(line))
            if matches:
                rows.append(dict(employer=job['employer'],title=job['title'],areas=job['areas'],source=url,section=heading,text=line,
                                 mentions=[dict(text=m.group(),start=m.start(),end=m.end()) for m in matches],review_status="unlabeled"))
    return rows

def collect(item):
    slug,allowed=item
    provider,board=slug.split(':',1)
    api={"lever":f"https://api.lever.co/v0/postings/{board}",
         "greenhouse":f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
         "ashby":f"https://api.ashbyhq.com/posting-api/job-board/{board}"}[provider]
    params={"lever":{"mode":"json"},"greenhouse":{"content":"true"},"ashby":{}}[provider]
    response=requests.get(api,params=params,timeout=25)
    response.raise_for_status()
    payload=response.json()
    rows=[]
    for post in (payload if provider=="lever" else payload["jobs"]):
        url=post[{"lever":"hostedUrl","greenhouse":"absolute_url","ashby":"jobUrl"}[provider]].split("?")[0].rstrip("/")
        if url not in allowed: continue
        job=allowed[url]
        if provider=="lever":
            sections=[(s['text'],s['content']) for s in post.get('lists',[])]
            sections.extend((key,post.get(key,'')) for key in ('descriptionPlain','additionalPlain'))
        else:
            body=unescape(post.get("content","")) if provider=="greenhouse" else post.get("descriptionHtml","")
            sections=[("description",body)]
        rows.extend(extract_passages(job,url,sections))
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--inventory',type=Path,required=True)
    ap.add_argument('--unclassified',action='store_true',help='Collect only titles outside tracked role families, for auxiliary research.')
    args=ap.parse_args()
    inv=json.loads(args.inventory.read_text('utf8'))
    groups={}
    for j in inv['jobs']:
        for provider,host in (("lever","jobs.lever.co"),("greenhouse","job-boards.greenhouse.io"),("ashby","jobs.ashbyhq.com")):
            m=re.fullmatch("https://"+re.escape(host)+r"/([^/]+)/(?:jobs/)?[^/?]+/?",j['url'])
            if m and bool(j['areas']) != args.unclassified: groups.setdefault(provider+":"+m[1],{})[j['url'].rstrip('/')]=j
    date=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest=ROOT/'data/raw'/(('unclassified-duration-' if args.unclassified else 'duration-')+date);dest.mkdir(parents=True)
    failures={};rows={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={slug:pool.submit(collect,(slug,jobs)) for slug,jobs in groups.items()}
        for slug,f in futures.items():
            try:
                for r in f.result(): rows[(r['source'],r['section'],r['text'])]=r
            except requests.RequestException as e: failures[slug]=str(e)
    out=list(rows.values())
    (dest/'candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in out),'utf8')
    report=dict(role_scope="unclassified_titles" if args.unclassified else "tracked_titles",collected_utc=date,inventory=args.inventory.name,boards_requested=len(groups),failed_boards=failures,
                inventory_urls=sum(map(len,groups.values())),urls_with_mentions=len({r['source'] for r in out}),
                employers_with_mentions=len({r['employer'] for r in out}),section_passages=len(out),
                unique_normalized_texts=len({r['text'].casefold() for r in out}),duration_mentions=sum(len(r['mentions']) for r in out),
                passages_by_host=dict(Counter(r["source"].split("/")[2] for r in out)),reviewed_labels=0,sha256=sha256((dest/'candidates.jsonl').read_bytes()).hexdigest())
    (dest/'summary.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(dest);print(report)

if __name__=='__main__': main()
