"""Compare direct classification with manual decomposition of AND requirements."""

import hashlib
import json

import torch
from train_pair_encoder import ROOT, LABELS, AutoModelForSequenceClassification, AutoTokenizer, encode


def combine(labels):
    if all(label=="supported" for label in labels):
        return "supported"
    if all(label=="unverified" for label in labels):
        return "unverified"
    return "partial"


def metrics(truth, predicted):
    pairs=list(zip(truth,predicted,strict=True))
    return dict(total=len(pairs),correct=sum(t==p for t,p in pairs),partial_found=pairs.count(("partial","partial")),
                false_full=sum(t!="supported" and p=="supported" for t,p in pairs))


def main():
    torch.set_num_threads(4)
    path=ROOT/"data/compound_evidence_dev.jsonl"
    rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
    original=[dict(requirement=r["requirement"],cv_passage=r["cv_passage"]) for r in rows]
    atomic=[dict(requirement=part,cv_passage=r["cv_passage"]) for r in rows for part in r["components"]]
    assert all(len(r["components"])==len(r["component_labels"])==2 for r in rows)
    truth=[combine(r["component_labels"]) for r in rows]
    report=dict(dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),results={})
    for name in ("pair-mentions-v3","pair-switch-tr"):
        checkpoint=ROOT/"runs"/name
        model=AutoModelForSequenceClassification.from_pretrained(checkpoint).eval()
        tokenizer=AutoTokenizer.from_pretrained(checkpoint)
        with torch.inference_mode():
            indices=model(**encode(original+atomic,tokenizer)).logits.argmax(1).tolist()
        predictions=[LABELS[i] for i in indices]
        direct,parts=predictions[:len(rows)],predictions[len(rows):]
        nested=[parts[i:i+2] for i in range(0,len(parts),2)]
        combined=[combine(pair) for pair in nested]
        result=dict(direct=metrics(truth,direct), decomposed=metrics(truth,combined),
                    components=metrics([t for r in rows for t in r["component_labels"]],parts))
        print(name,result)
        result["cases"]=[dict(family=r["family"],target=t,direct=d,parts=p,combined=c) for r,t,d,p,c in
                         zip(rows,truth,direct,nested,combined,strict=True)]
        report["results"][name]=result
    (ROOT/"reports/compound-evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
