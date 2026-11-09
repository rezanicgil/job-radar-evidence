"""Compare section-derived training signals with the released English sentence selector."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
from html import unescape
import io
import json
from pathlib import Path
import re

import requests
from huggingface_hub import hf_hub_download
from market_skills import HEADINGS
from skill_sentence_baseline import DATA,VERSION,ROOT,fit_counts,metrics,score,tokens

STATS=ROOT/"data/section-training-counts.json"
INDEX=ROOT/"releases/match-pilot/section_training_index.jsonl"


def index_digest():
    return sha256(INDEX.read_text(encoding="utf-8").encode()).hexdigest()


def normalized(text):
    return " ".join(text.casefold().split())


def reference_splits():
    seen=set()
    splits={}
    for split in ("train","dev","test"):
        path=hf_hub_download(DATA,split+".json",repo_type="dataset",revision=VERSION)
        rows=[]
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            row=json.loads(line)
            text=" ".join(row["tokens"])
            key=normalized(text)
            if key not in seen:
                rows.append((text,int(any(tag!="O" for tag in row["tags_skill"]+row["tags_knowledge"]))))
                seen.add(key)
        splits[split]=rows
    external=json.loads((ROOT/"reports/external-skill-recall.json").read_text(encoding="utf-8"))
    source=requests.get(external["source"],timeout=20)
    source.raise_for_status()
    if sha256(source.content).hexdigest()!=external["source_sha256"]:
        raise ValueError("External evaluation file changed")
    external_texts={normalized(row["sentence"]) for row in csv.DictReader(io.StringIO(source.text))}
    train_dev={normalized(t) for split in ("train","dev") for t,_ in splits[split]}
    return splits,sorted(external_texts-train_dev),seen|external_texts


def collect(path,excluded):
    records={}
    benefits={"why appnation","what we offer","compensation & benefits","benefits"}
    positive=HEADINGS["qualifications"]|HEADINGS["preferences"]
    for board,job,heading,body in json.loads(path.read_text(encoding="utf-8")):
        section=normalized(heading.replace("’","'")).rstrip(":?")
        if section not in positive|benefits:
            continue
        for index,item in enumerate(re.findall(r"<li\b[^>]*>(.*?)</li>",body,re.I|re.S)):
            text=" ".join(unescape(re.sub("<[^>]+>"," ",item)).split())
            key=normalized(text)
            if not key or key in excluded:
                continue
            label=int(section in positive)
            row=dict(url=f"https://jobs.lever.co/{board}/{job}",board=board,heading=heading.strip(),
                     bullet=index+1,text_sha256=sha256(key.encode()).hexdigest(),weak_label=label)
            if key not in records:
                records[key]=row
            elif records[key] is not None and records[key]["weak_label"]!=label:
                records[key]=None
    counts=[Counter(),Counter()]
    kept=[row for row in records.values() if row is not None]
    for text,row in records.items():
        if row is not None:
            counts[row["weak_label"]].update(tokens(text))
    INDEX.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in kept),encoding="utf-8")
    STATS.write_text(json.dumps(dict(source_cache_sha256=sha256(path.read_bytes()).hexdigest(),
        index_sha256=index_digest(),counts=counts),sort_keys=True,indent=2)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect",type=Path,help="Optional JSON cache of [board, posting ID, heading, list HTML] rows")
    args=parser.parse_args()
    splits,external,excluded=reference_splits()
    if args.collect:
        collect(args.collect,excluded)
    stats=json.loads(STATS.read_text(encoding="utf-8"))
    if stats["index_sha256"]!=index_digest():
        raise ValueError("Training index and counts differ")
    weak=[json.loads(s) for s in INDEX.read_text(encoding="utf-8").splitlines()]
    if {r["text_sha256"] for r in weak}&{sha256(s.encode()).hexdigest() for s in excluded}:
        raise ValueError("Weak training data overlaps reference data")
    train=splits["train"]
    counts=[Counter(),Counter()]
    for text,label in train:
        counts[label].update(tokens(text))
    original_positive=sum(y for _,y in train)
    baseline=fit_counts(counts,original_positive,len(train))
    for label in (0,1):
        counts[label].update(stats["counts"][label])
    positives=original_positive+sum(r["weak_label"] for r in weak)
    candidate=fit_counts(counts,positives,len(train)+len(weak))
    gold=[y for _,y in splits["dev"]]
    for model in (baseline,candidate):
        scores=[score(s,model) for s,_ in splits["dev"]]
        model["threshold"]=max(range(-20,21),key=lambda t:metrics(gold,[s>=t for s in scores])["f1"])
    report=dict(weak_rows=len(weak),weak_positive=sum(r["weak_label"] for r in weak),weak_boards=len({r["board"] for r in weak}),
                weak_postings=len({r["url"] for r in weak}),skillspan_revision=VERSION,results={})
    for name,model in [("released",baseline),("augmented",candidate)]:
        test=splits["test"]
        report["results"][name]=dict(threshold=model["threshold"],
            skillspan_test=metrics([y for _,y in test],[score(s,model)>=model["threshold"] for s,_ in test]),
            external_found=sum(score(s,model)>=model["threshold"] for s in external),external_total=len(external))
    (ROOT/"runs/section-selector.json").write_text(json.dumps(candidate),encoding="utf-8")
    (ROOT/"reports/section-training.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(report)


if __name__=="__main__":
    main()
