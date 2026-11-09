"""Measure exact knowledge-phrase boundaries on completed independent review rows."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/"releases/static-space/span-review-packet.json"


def read_decisions(path,packet,version):
    decisions={}
    for line in path.read_text("utf-8-sig").splitlines():
        row=json.loads(line)
        if row.get("format")!="job-radar-knowledge-review-v1" or row.get("packet_sha256")!=version:
            raise ValueError("Review format or packet revision mismatch")
        key=row.get("id")
        if key not in packet or key in decisions:
            raise ValueError("Unknown or duplicate bullet")
        spans=row.get("spans")
        if not isinstance(spans,list):
            raise ValueError("Missing completed span list")
        end=0
        for pair in spans:
            if (not isinstance(pair,list) or len(pair)!=2 or any(type(i) is not int for i in pair)
                    or not end<=pair[0]<pair[1]<=packet[key]["length"]):
                raise ValueError("Expected sorted non-overlapping Unicode offsets")
            end=pair[1]
        decisions[key]=set(map(tuple,spans))
    if not decisions:
        raise ValueError("No completed decisions")
    return decisions


def metrics(gold,pred):
    tp=fp=fn=0
    for key,spans in gold.items():
        guessed=pred[key]
        tp+=len(spans&guessed)
        fp+=len(guessed-spans)
        fn+=len(spans-guessed)
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,f1=2*tp/(2*tp+fp+fn) if tp+fp+fn else None)


def evaluate(paths):
    packet={row["id"]:row for row in json.loads(PACKET.read_bytes())}
    version=sha256(PACKET.read_bytes()).hexdigest()
    published=json.loads((ROOT/"reports/turkish-technology-mentions.json").read_text("utf8"))
    models={name:{r["text_sha256"]:set(map(tuple,r["predicted_offsets"])) for r in data["cases"]}
            for name,data in published["models"].items()}
    assert all(packet.keys()==pred.keys() for pred in models.values())
    reviews=[read_decisions(path,packet,version) for path in paths]
    report=dict(packet_sha256=version,packet_bullets=len(packet),reviews=[])
    for review in reviews:
        report["reviews"].append(dict(completed=len(review),empty=sum(not v for v in review.values()),
            models={name:metrics(review,pred) for name,pred in models.items()}))
    if len(reviews)==2:
        left,right=reviews
        shared=left.keys()&right.keys()
        consensus={k:left[k] for k in shared if left[k]==right[k]}
        report["comparison"]=dict(shared=len(shared),identical=len(consensus),disputed=sorted(shared-consensus.keys()),
            consensus_scores={name:metrics(consensus,pred) for name,pred in models.items()})
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("review",type=Path)
    cli.add_argument("--second",type=Path)
    args=cli.parse_args()
    print(json.dumps(evaluate([args.review,args.second] if args.second else [args.review]),indent=2))
