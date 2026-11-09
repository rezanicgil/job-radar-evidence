"""Evaluate frozen sentence selectors on deduplicated mobile employer sections."""
from collections import defaultdict
from hashlib import sha256
from html import unescape
import json
import re

import requests
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from market_inventory import ROOT
from skill_sentence_baseline import metrics,score
from train_section_selector import normalized,reference_splits

SNAPSHOT="skill-mentions-2026-11-09T200048374860Z.json"
INDEX=ROOT/"releases/match-pilot/mobile_section_index.jsonl"
HEADINGS={"requirements":"required","about your experience":"required","what we're looking for":"required",
          "nice to have":"preferred","why you should join yassir":"benefits","what we offer":"benefits"}


def sections(job,workable):
    if job["employer"]=="Lucida AI":
        key=job["url"].strip("/").split("/")[-1]
        return re.findall(r"<h3>([^<]*)</h3>\s*<ul>(.*?)</ul>",workable[key],re.S|re.I)
    board,key=job["url"].split("/")[-2:]
    response=requests.get(f"https://api.lever.co/v0/postings/{board}/{key}",timeout=15)
    response.raise_for_status()
    return [(s["text"],s["content"]) for s in response.json()["lists"]]


def main():
    published=json.loads((ROOT/"reports"/SNAPSHOT).read_text("utf8"))
    jobs=[p for p in published["postings"] if p["employer"] in {"Lucida AI","Yassir"} and
          set(p["areas"]) & {"iOS","Android","Mobile (general/cross-platform)"}]
    response=requests.get("https://www.workable.com/api/accounts/lucida-ai?details=true",timeout=15)
    response.raise_for_status()
    workable={p["shortcode"]:p["description"] for p in response.json()["jobs"]}
    _,_,reference=reference_splits()
    excluded={sha256(t.encode()).hexdigest() for t in reference}
    excluded.update(json.loads(s)["text_sha256"] for s in (ROOT/"releases/match-pilot/section_training_index.jsonl").read_text("utf8").splitlines())
    groups=defaultdict(list)
    texts={}
    for job in jobs:
        for heading,body in sections(job,workable):
            kind=HEADINGS.get(normalized(heading).replace("’","'"))
            if not kind:
                continue
            for position,bullet in enumerate(re.findall(r"<li\b[^>]*>(.*?)</li>",body,re.S|re.I),1):
                text=" ".join(unescape(re.sub("<[^>]+>"," ",bullet)).split())
                key=sha256(normalized(text).encode()).hexdigest()
                if not text or key in excluded:
                    continue
                texts[key]=text
                groups[key].append(dict(url=job["url"],employer=job["employer"],section=heading.strip(),
                                        section_kind=kind,bullet=position))
    rows=[dict(text_sha256=k,section_kind=v[0]["section_kind"],sources=v) for k,v in sorted(groups.items())
          if len({s["section_kind"] for s in v})==1]
    expected={p["url"] for p in jobs}
    assert expected and expected=={s["url"] for r in rows for s in r["sources"]}
    batch=[texts[r["text_sha256"]] for r in rows]
    browser=json.loads((ROOT/"releases/static-space/skill-sentences.json").read_text("utf8"))
    predictions={"browser":[score(t,browser)>=browser["threshold"] for t in batch]}
    torch.set_num_threads(4)
    for name,checkpoint in [("fine_tuned","skill-sentences"),("section_adapted","skill-section-adapted")]:
        tokenizer=AutoTokenizer.from_pretrained(ROOT/"runs"/checkpoint)
        model=AutoModelForSequenceClassification.from_pretrained(ROOT/"runs"/checkpoint).eval()
        with torch.inference_mode():
            logits=model(**tokenizer(batch,padding=True,truncation=True,max_length=96,return_tensors="pt")).logits
        predictions[name]=logits.argmax(1).tolist()
    results={}
    for employer in ["all",*sorted({p["employer"] for p in jobs})]:
        ids=[i for i,r in enumerate(rows) if employer=="all" or any(s["employer"]==employer for s in r["sources"])]
        labels=[rows[i]["section_kind"]!="benefits" for i in ids]
        results[employer]=dict(unique=len(ids),positive=sum(labels),methods={name:metrics(labels,[bool(pred[i]) for i in ids])
                               for name,pred in predictions.items()})
    INDEX.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),"utf8")
    report=dict(snapshot=SNAPSHOT,index_sha256=sha256(INDEX.read_text("utf8").encode()).hexdigest(),
                postings=len(jobs),source_pointers=sum(len(r["sources"]) for r in rows),results=results)
    (ROOT/"reports/mobile-section-transfer.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(json.dumps(report))


if __name__=="__main__":
    main()
