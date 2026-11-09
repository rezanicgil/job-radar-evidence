"""Compare the 105-pair checkpoint with training that adds fixed-CV contrasts."""

from collections import defaultdict
from hashlib import sha256
import json

import torch
from train_pair_encoder import BASE, REVISION, ROOT, LABELS, AutoTokenizer, AutoModelForSequenceClassification, encode, run


def score(rows, predictions):
    pairs=list(zip((r["label"] for r in rows),predictions,strict=True))
    return dict(total=len(rows),correct=sum(a==b for a,b in pairs),
                partial_found=pairs.count(("partial","partial")),
                false_full=sum(b=="supported" and a!="supported" for a,b in pairs),
                predictions=predictions)


def main():
    torch.set_num_threads(4)
    root=ROOT/"releases/match-pilot"
    files=dict(train=root/"train.jsonl",employer=root/"employer_tr.jsonl",
               additions=ROOT/"data/match_switch_training.jsonl",switch=root/"requirement_switch.jsonl",
               source=root/"source_validation.jsonl",validation=root/"validation.jsonl")
    rows={k:[json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()] for k,p in files.items()}
    training=rows["train"]+rows["employer"]+rows["additions"]
    splits=("switch","source","validation")
    dev=[r for name in splits for r in rows[name]]
    for name in ("additions","switch"):
        groups=defaultdict(list)
        for r in rows[name]:
            groups[r["cv_passage"]].append(r)
        assert all(len(g)==3 and {r["label"] for r in g}==set(LABELS) and
                   len({r["requirement"] for r in g})==3 for g in groups.values())
    for field in ("family","requirement","cv_passage"):
        assert {r[field] for r in training}.isdisjoint(r[field] for r in dev)
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    baseline=AutoModelForSequenceClassification.from_pretrained(ROOT/"runs/pair-employer-tr").eval()
    with torch.inference_mode():
        before=[LABELS[i] for i in baseline(**encode(dev,tokenizer)).logits.argmax(1).tolist()]
    after=run(training,dev,tokenizer,True,"switch-tr")["predictions"]
    report=dict(base=BASE,revision=REVISION,seed=17,epochs=6,learning_rate=5e-5,
                baseline_pairs=len(training)-len(rows["additions"]),augmented_pairs=len(training),
                hashes={k:sha256(p.read_bytes()).hexdigest() for k,p in files.items()},results={})
    for method,predictions in (("baseline",before),("augmented",after)):
        start=0
        results={}
        for name in splits:
            batch=rows[name]
            segment=predictions[start:start+len(batch)]
            results[name]=score(batch,segment)
            if name=="switch":
                grouped=defaultdict(list)
                for r,p in zip(batch,segment,strict=True):
                    grouped[r["cv_passage"]].append((r["label"],p))
                results[name]["families_changed"]=sum(len({p for _,p in g})>1 for g in grouped.values())
                results[name]["families_all_correct"]=sum(all(t==p for t,p in g) for g in grouped.values())
            start+=len(batch)
            print(method,name,{k:v for k,v in results[name].items() if k!="predictions"})
        report["results"][method]=results
    (ROOT/"reports/switch-training.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
